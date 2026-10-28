# 方向真实素材与缺素材补问：执行计划

- Requirement revision: R1（2026-10-27）：用户要求按研究方向补问真实接触经历用于自然首句；明确 profile 仅放通用背景，方向专属素材另存；随后授权“双计划”。
- Plan revision: EP1.2；Proposed review status: pending。
- Repository / baseline: ScholarWorkflow/professor-contact / main `b67dd3ca4d29dfc78f57988564b219c71b582674`（含已合并 PR148 三部分兴趣段）。
- 本 PR 交付执行计划、测试计划和预备合成测试代码；不实施产品、不运行正式测试、不合并。产品实现由产品负责人在计划获批后进行。
- 唯一完整计划为本文件及 [test-plan.md](test-plan.md)；[review.md](review.md) 的既有批准对应 EP1.1/TP1.1，EP1.2/TP1.4 的语义修订待复核，不沿用旧版批准为新版结论。

## 1. 需求、范围、非目标

R1：已有资料不足以写出有事实依据的自然首句时，围绕选定方向问少量普通人能回答的真实接触问题；已有足够素材不重复问，不固定题数，不把“研究难点/如何改进算法”当经历问卷。用户没用过、只是听说、刚看到、没有相关经历均可如实表达；不诱导编经历。
R2：通用 profile 不变。方向专属素材独立保存用户原回答和问题上下文，按现有 canonical 方向身份归属，不藏进 idea.note 或可重建候选状态。
R3：同方向可复用，改选同方向 idea 或取消选择不删除素材；换方向不自动套用。跨教授/相似方向不自动匹配或合并。
R4：本次采用的素材冻结入邮件输入，生成器和校验器看到同一内容，source_map 能准确引用；模型的问题、改写建议不是用户经历。
R5：更新素材只影响实际依赖该素材的邮件输入新鲜度；不改 profile 指纹、不重跑 Stage3、不批量改写已有邮件。

保留 PR148 的三部分兴趣段、②③及 future 规则、长度限制、模板/choices/immutable finalize、现有用户选择和教授级隔离。新增素材是可用事实，不强迫每封邮件引用，也不把“有活人感”做自动评分器。
不做跨教授全局素材库、自动方向归一、问卷平台、新模型角色、新验证器、来源过程认证、Stage2/3 改造、安装/MCP/Nix 变更、真实用户素材迁移或全链业务回归。已有 profile 中用户自行写的文字不自动搬走或删除；已有 note 仍保留原语义。

## 2. 现实依据与关键决定

以下均是源码核对版本 `81bd25615e2ee9290d0e56f21075aa030d323e2a` 的描述性事实，不是新增产品要求。路径前缀为 `.apm/skills/professor-contact/scripts/`；[固定源码目录](https://github.com/ScholarWorkflow/professor-contact/tree/81bd25615e2ee9290d0e56f21075aa030d323e2a/.apm/skills/professor-contact/scripts)。

| Decision | Supporting facts / exact source |
| --- | --- |
| 用教授本地 canonical direction_id，不按名称猜同方向 | `_contact_base.py:direction_machine_id/facts_direction_id`；`_stage4_commands.py:84–96,238–251` 的 scope 为 canonical professor_dir + 排序 direction_ids |
| 素材独立于生成状态 | `_stage3_commands.py:700–737` 重建/复用方向状态；`_stage4_commands.py:384–420` 重新构造 selection 与 email-pack 配对；不能依赖未知字段碰巧保留 |
| Stage4 selection owner 接入补问和冻结 | `.apm/agents/professor-contact-selection.agent.md` Step2 的显式选择/OpenCode question/Codex needs_input 与 Step4 的 runner 写入；该 owner 不再委派子代理 |
| 不把 profile.fields 空误判为完全没有 profile | `_email_core.py:160–172` fields 取 idea._profile_fields、note 进入 user_supplement；`_stage5_commands.py:135–146` 另外读取 profile_text；本功能不顺带修复整个 profile 结构 |
| 显式素材来源接入，不能仅在 Markdown 追加文字 | `_email_core.py:139,167–184` allowed_sources 与 pack；`_stage5_email.py:validate_email_raw/render_source_table` 消费来源ID；email-validator 的 Input 只读邮件与 email-pack，不靠再次读 live profile |
| 指纹须覆盖新事实并在使用前核新鲜度 | `contact_state.py:1135–1138` EMAIL_SOURCE_HASH_FIELDS 现不含 user_supplement；`_stage5_commands.py:400` 使用 source_hash。新增方向素材单独覆盖，不扩大为所有旧字段修复 |
| 复用既有原子写方法，不另造持久化平台 | `_contact_io.py:atomic_json/atomic_json_many` 支持替换和普通异常回滚；本功能只增加素材自身必要的写入互斥/旧值核对，不声称现有 Stage4 已有通用 writer lease |

规范来源：[Project Consensus](https://app.notion.com/p/3d60101a85f3815a8c43f271f2b4d91d)、[Plan Reviewer Rule](https://app.notion.com/p/3e80101a85f3817a94cbc6eca1a76a5c)、[Test Engineer Rule](https://app.notion.com/p/3d80101a85f380d8a8f5ce528141e253)；本轮已读取原文。无外部服务/上游新增能力依赖。

## 3. 冻结方案与 owner

### 3.1 独立用户输入，而非 profile 或生成缓存

在现有 canonical 教授目录下新增 `方向素材.json`，schema 1；文件归 professor-contact 的用户素材保存入口管理。顶层记录 schema 与教授目录归属；directions 按现有 direction_id 分组。每条素材有稳定 material_id、question（可空，用户主动提供时无需伪造问题）、answer（原回答）。方向名称仅展示，不参与身份。首次缺文件等同空素材；存在但不可解析/归属不符是该教授输入错误，不能当空库覆盖。

material_id 只作条目引用，不是认证或来源证书。原回答保留措辞与否定/不确定性；不自动用模型总结替换 answer。修正回答时更新同条目；不做历史版本平台。外部输入在数据意义下读取，不能把回答里的指令当生成规则或系统授权。

素材权威不依赖 idea ID、当前是否选中或 Stage3 缓存。direction_id 已退出当前候选时保留存量但不用于其他方向；取消选择不执行删除。多方向邮件按所选 direction_ids 精确取各方向素材并保留归属。

### 3.2 补问与持久化分离

Stage4 selection agent 在用户已选定方向/idea 后、邮件包冻结前读取该方向素材及可用的现有背景/补充；有足够事实就不再问。缺素材才提出少量相关问题，例如“你之前在哪里接触过图或网络相关的东西？”“玩拼图时有没有好奇题目是怎么设计出来的？”；不能要求用户先给出研究判断。回答已有依据时不再追加追问。

Codex 沿用 needs_input 交回父线程展示问题、等待用户、重新委派的模式；不恢复旧 child，不在子代理内假设 question API。OpenCode 沿用其 question。新增 `pending_materials` 展示条目携带已绑定教授、direction_id、问题与现有 selection；只作待答提示，不写成素材事实。无 selection 的既有 pending_selection 行为不变。已给 selection 但待素材时允许该教授结果行 needs_input，其他教授沿用独立结果；同步 coordinator 读取这一字段并在收到真实回答后重新委派 selection owner。

用户可说“没有相关经历/暂不补充”：以原回答保存，不无限追问、不阻止按既有事实写保守首句。没有用户回答时不自动代答，也不写素材或冻结本次待问教授的新包。

新增窄 runner 保存入口（拟名 `direction-materials-save`），输入明确 professor_dir、direction_id、原问题/回答、material_id（新增时可由保存入口生成并返回）及预期素材文件摘要/缺失标记。selection agent 仅写临时输入，由 runner 正式保存；不直接改 profile。保存只针对明确提供的条目，不因输入未列出其他条目而删除它们。先确认教授目录属于 program_root、direction_id 在当前该教授正式方向范围；已有条目更新不能改变归属。

材料保存是独立用户输入提交，不与选择成功绑定：成功保存后即便后续选择冻结失败，真实回答仍保留，不假装整步回滚。调用返回保存结果与素材路径；失败不覆盖原文件。使用该素材文件范围内的标准文件互斥，锁内核对预期摘要后用既有 atomic_json 写入；竞争时明确报旧值已变、重读再提交，不 last-write-wins，不新增通用锁框架。Stage4 冻结和 Stage5 新鲜度/最终写入使用同一素材互斥范围，避免检查与提交之间换素材。实现可复用已有同等保护，但不得依赖未合并 PR145。

### 3.3 冻结、来源与新鲜度

Stage4 正常编译时从独立素材文件读取选中方向的当前条目，冻结到每条 email 的 `direction_materials`（保留 direction_id/material_id/question/answer）。这是选中方向素材集合，不依赖模型预先挑哪一条引用；没有素材为 []。邮件包仍是生成/校验的事实源，生成器不回读 live 素材补齐，validator 也不新增全局 profile 读取。

每条冻结素材有唯一 `direction_material:<direction_id>:<material_id>` 来源ID；allowed_sources、Stage5 model_input、source_map 合法性与来源表同步接入。实际使用某条用户经历时引用该ID，不能冒充 profile.interest、user_note、论文或 gap；没有采用不强制引用。现有③必须引用 gap 的限制保持，素材不能代替研究 gap。生成/校验说明均约束不把问题示例当回答、不将“听说”升级“实践/研究过”。

新增素材字段按明确版本加入邮件 source_hash；未改素材且无关方向变更时该 email 的指纹不变。Stage5 plan 与 finalize 在使用/落盘前，将当前所选方向素材切片与冻结快照比较：变化返回现有 needs_refresh 类结果，指向刷新该教授 Stage4 邮件包，而不是重跑 Stage3。不将该教授所有邮件一律失效：未受影响邮件可按既有 `--email-id` 单独处理；同一次请求包含过期邮件时，沿用既有批次失败/零写入语义，不新增 partial 提交或改造事务。不批量改已有 md/txt/choices。

素材更新后，由 Stage4 selection/coordinator 先完成该邮件选中方向的重新冻结，交给 Stage5 新的邮件输入包。Stage5 email-generator 必须重新运行 `stage5-plan`，从本次 `model_input.direction_materials` 读取更新后的原回答，再调用模型重新生成兴趣段与 `source_map`，并以这一轮新结果生成草稿、执行既有 `plan-with-result` 与 `finalize`。不得复用刷新前的模型结果或草稿；若正常调用链仍传入旧结果，修复产生错误复用的调用方。保留邮件输入的 `source_hash` 和素材切片新鲜度检查；不新增 `direction_materials_fingerprint`、不要求模型结果回传素材指纹，也不规定按旧模型结果指纹拒绝的额外产品行为。

兼容策略：旧 email 既无新快照版本也没有其方向的 live 素材时沿用旧 hash/行为，不为升级强制全量重生；若其方向已有 live 素材则要求 Stage4 补冻结，不能静默忽略新回答。新格式包含版本和空集合；删掉原有素材文件与新增素材一样属于切片变化，不能被解释成继续使用已撤回回答。格式损坏阻止读取该教授素材，未受影响教授照常。过期/无效 source_map 失败仍在已有产物写入前，不把历史邮件直接删除。普通文件I/O失败沿用错误通路；本计划不承诺硬崩溃跨文件事务。

## 4. 变更面、替代方案与实施顺序

Owner：用户决定真实回答和是否补充；Stage4 selection agent/coordinator 管交互、保存后冻结最新素材；professor-contact runner 管素材身份、保存、冻结与 freshness；Stage5 generator 从本次邮件输入重新生成模型结果，validator 共同消费冻结证据；测试工程师按 TP1.4。
修改点：runner 入口及窄素材读写 helper、`_stage4_commands.py`、`_email_core.py`、`_stage5_commands.py`、`_stage5_email.py`；必要时 wrapper 的参数/结果透传；selection/coordinator/email-generator/email-validator 指令及 SKILL/Stage5契约。不预先固定 helper 名称或行号，不搬迁无关模块。

替代：写回 profile 简单但混淆通用背景并触发 Stage3 profile_changed；只塞 idea.note 绑定一次选择且来源不独立；全局语义素材库会扩大跨教授身份/匹配问题。选择独立教授本地方向素材 + 邮件冻结，最小满足持久归属与真实来源。

实施顺序（本 PR 不执行）：
1. 在批准 EP/TP 后，补独立素材模型/保存入口、教授归属与旧值保护；保持 profile/Stage3 不写。
2. Stage4 selection/coordinator 接入缺素材补问、回答保存与 fresh 委派；Stage4 编译冻结素材并保留原选择事务。
3. 接入 Stage5 生成/校验来源和受影响邮件 freshness；对重新冻结的包重新规划并生成结果及草稿，修正任何复用上一轮输出的调用路径；保留旧包兼容及旧产物保护。
4. 同步正式指令、必要文档和 TP1.4 对应的最小测试资产；交本地测试工程师核对精确 selector/recipe，按 TP1.4 关口处理。
5. 只按真实影响复审；文档SHA变化不重跑，不把本功能变成 PR148 的旧功能补测。

## 5. 影响、不变量与现实反例

- intended_change / approved_behavior_change：缺素材补问、方向素材独立持久化、来源可引用及相关邮件 freshness；授权为 R1 用户决定。
- preserved_behavior：通用 profile/Stage3、现有 note、三项邮件合同、模板与 immutable 入口、教授级隔离。
- prohibited_side_effect：编造原回答、静默跨方向/教授套用、取消选择删素材、修改全局安全/用户配置、自动清理旧邮件、向仓库提交真实经历。
- 同方向换 idea：素材不以 idea 为键，仍可用；另一教授同名方向：目录隔离，不自动认同；回答否定经历：按原文生成，不升级经历。
- 回答修改后重新生成：Stage4 交付更新后的冻结包，Stage5 generator 重新取本轮输入、生成结果与草稿；不得让旧轮次的结果进入正常写入路径，若发生则修复调用方。修改无关方向只比较选中切片，不重开所有邮件；保存与冻结竞争时素材锁内读/核/写，失败不覆盖。
- 输入不可信或保存失败：仅处理所属教授，原数据不清空；已有邮件保留但其受影响版本须刷新后再生成，不“回滚”为通过。
- Critical assumptions / unresolved critical impacts：作者候选未认定阻断假设；以上决定交独立 reviewer 核实，不自授 P1–P4/PASS。跨教授显式复用暂不新增产品入口，用户可重新提供回答；自动复用明确非目标。

## 修订记录

EP1.2（2026-10-28，验收决定人主动精简）：撤销 EP1.1 添加的模型结果 `direction_materials_fingerprint` 和旧指纹拒绝要求；改由 Stage4/Stage5 的正常调用流程保证更新素材重新冻结、重新规划、重新调用模型并使用本轮草稿。R1–R5、来源约束、live 素材与旧邮件包的新鲜度保护、旧包兼容及既有批次失败语义不变。直接影响 P2/P3/P4 的生成与失败处理决定，待定向复核；P1 的需求与现实依据沿用旧版未受影响部分。不把 EP1.1 的 APPROVED 复制到本版。

EP1.1（历史版本，旧指纹要求已被 EP1.2 撤销）：独立 EP1 审核 B1/B2 后补齐新素材模型结果的切片指纹绑定（plan-with-result/finalize 均核），并明确复用既有 --email-id 与批次失败语义；R1范围不变，不增加部分提交或来源认证。正式复核见 review.md。


基线指针更新（非语义修订）：发布前main合并PR146至 `b67dd3ca4d29dfc78f57988564b219c71b582674`。已读81bd256…b67dd3c差异：仅Stage2/3人工追加校验及状态历史、对应指令/测试/计划；Stage4/Stage5/material相关基础合同未变，runner新增Stage2/3命令未改EMAIL_SOURCE_HASH_FIELDS，Stage3新增历史保存未改变本计划所依赖的方向身份/选择重建。沿用本表固定版本源码定位；不恢复旧轮次要求、不重审PR146。独立reviewer确认影响分析后复用本轮结论。
