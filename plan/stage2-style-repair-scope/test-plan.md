# 测试计划：Stage 2 扫描与修订闭环
TP1.1；Requirement R1；baseline a67ca3b630e00941d8c72ad7328a8f7796bda77b。Independent review record: review.md（EP1.1 已批准；TP1.1 Gate1–3结论见该记录）。

## 必测清单（范围上限）
1. 扫描范围：合成方向同时含 narrative、freshness 解释、原文中译标题标签状态；prepare 只交付六类 narrative 和三类 freshness 解释，完整人读稿及来源不被改写。检查现有 unittest 的字段/文本断言。
2. 报错到修订：生成文本与固定标签跨界引用，narrative 正常生成修订 job，freshness 只授权原三字段；纯源/标签误报有明确 scope 错误且不写状态，不伪造 pass。真实结构问题保持明确 owner 交接。检查正式 runner 接口结果与文件状态。
3. 缺文案：无/空 summary、explanation 有可定位补写槽位（summary 非新增必填，explanation 保持原必填）；登记→refine-plan→refine-finalize→重校验能补文案，源 quote/translation/状态不变。检查现有合成 fixture 和正式 CLI 路径。
4. 绑定及兼容：旧布局走现有刷新入口；陈旧报告仍拒绝，默认轮次/续轮及三字段受控修复仍适用；Stage3 输入契约不改。复用既有测试中直接相关断言，不全仓回归。
5. 生产接线：人工只读核对 SKILL/caller/validator 的 prepare→scope→原稿定位→record→refine/repair 指示一致，Stage2 不再要求全文风格扫描，未屏蔽整张卡的模型解释。

## 方法与执行准备
在当前云端隔离工作区使用现有 Python unittest 与合成 BaseEnv；不安装、不调用真实模型、不触碰用户 Mac、真实教授资料或外部服务。新增本议题测试复用既有 fixture，不建判定器。准确命令、所选既有测试方法、输出目录见下方 recipe，由独立 reviewer 审 Gate2 后执行；当前不声明 Gate2 或执行通过。
每项选择一个足够入口；生产接线用源码复核，不为其另加真实模型调用。失败保留完整 unittest 输出于独立 /tmp 目录；业务失败先修产品，不改预期求通过；外部故障不自动重试，方法或产品修订只复验受影响项。不因计划/记录 SHA 变化重跑。

## TP1.1 执行 recipe（Gate2 记录见 review.md）
仅细化上述目标，不扩必测清单。工作目录 `/workspace/shared/contact-style-repair`，producer baseline 如上，候选产品/测试为本 PR diff。Python3 标准库 unittest；合成 fixture 自建临时资料目录。无需安装、模型或外部服务。运行前仅确认 `python --version` 与目标文件存在，依赖缺失按 preparation error，不标产品失败。

正式命令（从仓库根运行）：
```sh
RUN_DIR=$(mktemp -d /tmp/contact-style-scope.XXXXXX)
export PYTHONDONTWRITEBYTECODE=1
export TMPDIR="$RUN_DIR"
cd .apm/skills/professor-contact/tests
python -m unittest -v \
 test_stage2_style_repair_scope.Stage2StyleRepairScopeTests \
 test_stage2_source_evidence_repair.SourceEvidenceRepairTests \
 test_stage2_fixed_evidence.FixedEvidenceBase.test_u1_c_report_ownership_uses_real_fragments \
 test_stage2_fixed_evidence.FixedEvidenceBase.test_u1_d_narrative_two_rounds_and_fixed_stop \
 test_stage2_fixed_evidence.FixedEvidenceBase.test_u1_e_old_pack_updates_through_process_to_finalize \
 test_human_validation_continuation.Stage2ContinuationTests.test_c_a_extended_rounds_accumulate_and_keep_old_failures \
 >"$RUN_DIR/unittest.log" 2>&1
STATUS=$?
printf 'exit=%s\nlog=%s\n' "$STATUS" "$RUN_DIR/unittest.log"
```
目标1/2/3/新版迁移由新增 scope 测试覆盖；三字段窄授权及刷新复用原 repair 测试；现有 fixed-evidence C/D/E 只核受影响归属、周期和正常升级；人工续轮只选 Stage2 的 C-A，不运行 Stage3 或其余续轮组合。旧测试中将来源文风问题视为可登记错误的断言按获批新范围更新，结构 owner 路由保留，不删除保护目标。

目标5由独立 reviewer 只读检查本次生产接线 diff，记录具体入口与结果。标准 unittest 输出作为执行记录，不新建判定器。无自动重试；环境失败补齐现有依赖后再审受影响步骤，产品失败修实现后仅复验所涉目标，保留第一次失败日志。同次成功不覆盖此前失败。Gate3由非实现者确认实际结果有效性。
