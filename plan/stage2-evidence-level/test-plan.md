# Stage 2 固定证据与分析级别测试计划

- Test revision：contact-evidence-level-t6；对应 [执行计划 r4](implementation-plan.md)。
- Requirement revision：2026-10-17 用户授权的 U1/U5 修复；基线 `305bc08f8b186672108cffbba0293d249bc8b4b2`。
- 状态：设计与第一/第二关待审，第三关未执行。这里只准备计划，没有运行测试、补造结果或宣称修复完成。
- [Test Engineer Rule](https://app.notion.com/p/3d80101a85f380d8a8f5ce528141e253) 决定范围；附录/步骤不追加清单外检查。

## 1. 唯一必测清单

| 项 | 目标与输入 | 预期结果 | 足够的检查入口 |
|---|---|---|---|
| T1 | 同一既有夹具覆盖固定卡 evidence/completed_part/remaining_gap 及禁锚区 evidence 中已知编号，可信标题/链接已在当前材料；另一个缺可信题名的引用 | 正式 finalize 输出题名/链接，上述机器字段/候选编号与事实不变，其他说明原意、作者 quote/translation、用户笔记不变；缺题名明确失败且不生成伪引用 | 既有 runner CLI 测试夹具，检查 Markdown 与 pack 必要字段 |
| T2 | 当前受管正文上的固定区 blocking 与混合固定/叙事 blocking 原始报告；复用现有用户笔记/论文一览禁止区域报告 | 合法固定区第一轮失败确实登记；禁止区域报告继续拒绝且无 correction jobs；原始报告不改、非通过；refine-plan 无 jobs、明确交源/生成器处理，refine-finalize 不写；同内容重试不能清轮数。修复正式生成内容后普通 finalize 产生新正文，旧 PASS/失败不冒充新结果 | 既有 Stage2ValidationHandoffTests 的报告/正文夹具和 record/refine/finalize CLI |
| T3 | 纯 narrative 第一次失败→现有合法修订→第二次仍失败（可用第二轮新固定卡阻挡覆盖其归属）；及已绑定报告对应的正文/pack被改 | 纯文字修订仍可完成且第二次终态不继续第三轮；不允许用过期报告改事实或覆盖手改文件 | 复用该模块已有 second_blocking_round_is_terminal、stale_render、changed_input_pack 对应测试；只调整受新登记分类影响的断言 |
| T4 | 复用同一方向的 fulltext、abstract（有分析文件）、未确认（有 PDF，索引分析状态失败但残留旧 fulltext 级别）及 OCR-only fulltext/facts unavailable 夹具，并将 §2 已有缺 analysis_level 兼容样例归入本项（有分析文件/PDF 仍为未确认，不复制样例）；有完整接受基线且 /tmp facts 已不存在，原正文已有有效绑定 validator PASS，仅 level/render 变更由正式 preflight→展示刷新，同一场景复用 T1 已知引用及正式 pack 中可信题名/链接；在同一来源夹具中依次作新增、删除、替换分析依据（含原缺 facts 路径出现），并保留旧缺基线情形 | 三类计数/规范包一致，失败记录即使残留 fulltext、旧记录缺 analysis_level 即使有分析文件/PDF，均归未确认；同一 pack-only 刷新输出的固定卡 evidence/completed_part/remaining_gap 与禁锚区 evidence 均显示可信题名/链接，原始机器字段及候选编号不变；纯展示刷新使正文实质变化后，旧 validator PASS 不再被接受，不运行模型校验；等价重写仍不清轮数。纯展示后再预检不因过期包完整性摘要误 process，保留 assignment/模型指纹、不重签 proof、不额外生成分析/归属/时效任务；新增/删除/替换、无法比较的旧基线走原 process，不能误当 display-only；复用已有写前漂移/手改保护检查，不写不确定结果 | 既有 BaseEnv/preflight/pack-only 渲染及 guard 夹具，检查分流原因、pack/Markdown及任务记录；只覆盖这些直接反例，不交叉穷举，不跑真实模型 |

T1—T4 是上限。无需真实 Zotero、下载/PDF分析重跑、Nix/APM重装、全教授流程或完整测试模块回归；本次未改安装和模型业务。报告中“四位教授”与“10+1”是缺陷背景，不能强制采集私人材料或追加四次模型验收。

## 2. 实现后补齐可运行 recipe 的交接

- 产品测试放 `.apm/skills/professor-contact/tests/`，优先复用 `test_contact_state.py` 的 BaseEnv、run_cli、run_bound_stage2_finalize 及 `test_stage2_style_validation_handoff.py`，不新建判定框架。
- T1/T2/T4 的新增覆盖在现有适合模块增加最小方法；T2 另精确纳入既有 `test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_stage2_nonrepairable_user_note_does_not_create_a_correction_job` 选择器，沿用其禁止区域拒绝及零修订任务断言；T3 复用既有方法，不把整模块选入 recipe。实现者在本文件写明最终完整的 unittest module.Class.method 选择器和对应项；除上述已存在的 T2 选择器外，新增方法尚未实现，不能虚构可执行名称或将此草稿当作第二关已过。
- 更新受影响旧测试：仅允许校验的固定证据卡相关旧“登记必须失败”断言改为“失败可登记但模型不可修订”；用户笔记和固定论文表被明确跳过，原错误报告拒绝断言保持；新 facts/规范 paper fixtures 明确级别，旧缺 analysis_level 字段兼容样例保留并归入 T4，复用同一夹具和运行链。不要仅加新用例而让旧断言继续要求冲突行为。
- 准备：进入目标 producer checkout，确认实际产品/测试提交，使用仓库现有 Python 测试方式；不操作用户教授目录。现有 BaseEnv/临时目录已承担隔离，只将日志放新建 `/tmp/contact-evidence-level.XXXXXXXX`。没有外部服务和模型配置需求。
- 最终 recipe 形态：在 tests 目录运行 `python3 -m unittest <T1-T4实际选择器>`，记录 Python 版本、命令、退出码和简短标准报告。分项结果由现有断言判定，无新 JSON oracle。执行者在第一/第二关认可后按填好的命令运行，不在计划准备阶段运行。
- 若新测试需要改变现有共享 fixture，只改本任务所需字段/行为并检查直接调用处；不藉此要求全仓回归。实际接口因 PR91 合并改变时，仅同步受影响入参/结果与选择器，不引入 PR91 全套测试。

## 3. 失败、复验与结果

本次确定性测试无自动重试。产品断言失败原样保留；先修产品再复验受影响项。命令/环境错误记无法判断，修正错误后只重试受影响命令，保留此前记录。未执行不得填 PASS；后续清理错误不得覆盖已确认失败。

记录格式保持简单：实际提交、T1—T4逐项通过/业务失败/无法判断/未执行、实际命令与输出位置、复用结果来源、剩余问题及负责人。原始日志和临时数据在仓库外，公开提交仅必要脱敏摘要。

修订边界：t6 将执行 r4 §3.1 的 pack-only 可信引用展示断言接入 T4 已有展示刷新场景，并将 §2 已有缺 analysis_level 兼容样例明确归入 T4；复用 T1 引用及既有夹具，不复制样例或运行链。T1–T3、失败残留级别与旧校验失效预期及执行方案不变，不新增必测项或组合矩阵。执行 r4 已获[正式批准](https://github.com/ScholarWorkflow/professor-contact/pull/92#issuecomment-6228535516)，本次不重开其未受影响关口；测试设计及步骤仍待相应复核。

当前结果：T1、T2、T3、T4均未执行。测试计划工程师负责方案修订，本地测试工程师补最终选择器及步骤，独立审核者确认设计/执行步骤，产品负责人修实现；结果审核按实际证据开展。文档变更不触发已有效结果重跑。
