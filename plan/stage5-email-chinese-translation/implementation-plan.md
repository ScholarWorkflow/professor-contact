# Stage 5 邮件中文译文执行计划

- Requirement revision: user-2026-10-29-email-translation；用户要求邮件后附中文译文，并将本项独立 PR、双计划正常审核后云端实现。
- Plan revision: R1
- Target: ScholarWorkflow/professor-contact main `ad096fe31a4b5694cbe47a40f37b621435e1eeec`
- Proposed review status: pending（作者不自授 APPROVED）

## 需求、范围与非目标
首封及无回复跟进邮件 `.md` 的邮件正文之后、来源标注之前增加“中文译文（仅供核对，不发送）”，完整翻译最终日文 Subject 和正文，忠实保留事实、语气、否定和不确定性。译文只作用户核对，不能成为发送正文或论文事实源。发送 `.txt`、用户模板、既有日文生成/长度/三句兴趣结构、来源表/事实卡保持不变。不实现自动发送、翻译服务框架、批量迁移旧产物、论文分析链接或空格链接修复。

## 关键事实 → 决定
以下源码均指上述 target SHA：
1. `scripts/stage5_immutable.py::_immutable_finalize` 用 stage5-plan 的确定性 drafts 原样进入 finalize；`.apm/agents/professor-contact-email-generator.agent.md` 的 humanizer 约束仅允许组装前润色 dynamic fields。因此翻译安排在润色与 choices 完成后的最终组装文本上，绝不重新 humanize 整封模板。
2. `scripts/_stage5_commands.py::_stage5_plan_locked` 返回 initial/followup output_id + draft；`_stage5_finalize_locked` 提取 Subject/body 后分别构造 md 与 txt，全部准备完才写盘。因此由生产 runner 暴露统一规范化最终文本作为 translation_source，并在同一 prepare 阶段插入译文。
3. finalize 当前的 rendered_hashes/manual_markdown_changed 与 state_updates/prepared 保证手改保护和单教授写入边界。译文必须参与 md 原有 hash，不得 finalize 后再补写文件。
4. validator 当前检查整个邮件文档的业务片段，并未定义整封中文译文。必须明确日本语规则只作用于“邮件正文”，新增译文一致性核对而非中文套用日文标题逐字/三段/字数检查。
上述 scripts 均在 `.apm/skills/professor-contact/` 下。正式规范来源为本次用户授权；代码只是机制证据。

## 冻结方案及接口
- 抽取现有 Subject/body 规范化小 helper（不改变规范化行为），plan 和 finalize 共用。plan drafts 新增 `translation_source`，值严格为将写入 txt 的 `Subject: ...\n\n...\n`。不改变现有 `draft` 字段。
- generator 在最终动态字段和 choices 确定后执行现有 `stage5-plan --result --choices`，将每个选中 output_id 的 translation_source 当作唯一翻译原文；自己翻译，不另增 agent/服务。保存独立临时 JSON：`{output_id: {source_text: <原样 translation_source>, subject_zh: <中文件名>, body_zh: <完整中文正文>}}`。首封与跟进不得混用；翻译后不再修改日文，如有修改重新 plan/翻译受影响输出。
- finalize 新可选 `--translations <absolute JSON path>`；immutable wrapper 原样转发给 finalize，其内部 plan 不需要此参数。当前 named generator 必须提供完整选中译文文件；参数省略仍保留旧直接 CLI 的无译文行为，不强制改写旧文件/旧调用者。
- 参数存在时只消费本次选中 output_id。每个选中输出必须恰有一个对象，source_text 与实际最终 txt 精确一致，中文 subject/body 为非空字符串；不符合或文件无法读取即写盘前拒绝（translation_missing/translation_invalid/translation_stale）。普通 JSON 对象为唯一 output_id 映射，不另造授权或来源认证协议。规范源文本比较只防止译文对应旧邮件，不声称机器已判定翻译语义正确。
- Markdown 译文节插在邮件正文后，显示 `主题：...` 和中文正文；txt 从原有日文变量构造，完全不引用译文。继续既有 md hash 和手改拒绝语义。
- generator/SKILL 明确新增步骤与临时文件清理归属；validator 核对当前生成邮件的译文对应最终日文，不新增事实/夸大，缺译文或明显漏译/错译阻止当前新流程通过；已存在旧邮件无强制迁移。译文不是 source_map 的独立生成断言。

## 影响、安全与替代
- intended/approved change：当前正常 Stage 5 产物增加核对用中文；授权为本次用户请求。
- preserved：日文 txt 字节、用户模板、邮件身份 output_id、只处理选中邮件、单教授事务、手改 md 保护、验证缓存和源材料新鲜度关口。
- prohibited：译文进入 txt、改写模板、翻译旧稿/其他邮件、补造事实、跳过 cache/手改关口、把中文作为日文规则输入。
- 代表性反例：先翻译后润色会失配→source_text 比较拒绝；both 共用一份译文→独立 output_id；中译后补写→禁止，以 prepared 原子提交；旧 CLI 没有翻译参数→兼容保持，不制造新失败。
- 替代：finalize 后由模型直接 append md 更简单，但绕过 hash/原子性且可污染 txt，因此不选；外部翻译 API/专用 agent 增加无必要依赖，因此不选。
- 无新增上游依赖、全局设置或迁移；模型翻译语义必须由既有 validator/正式样例检查，离线机械测试不能代替。

## 实施顺序 / owner
1. 独立执行计划与测试计划审核；未批准不实现。
2. runner 统一最终文本与 translations 输入校验/渲染，保持旧接口兼容。
3. generator、SKILL、validator 接入最小翻译步骤/边界。
4. 按 test-plan 执行目标离线检查，正式模型测试如无授权可用环境如实待测。
5. 独立代码/结果审核后普通提交，新分支 Draft PR；不自动合并。

无未验证核心机制假设；正式模型质量是待执行验证，不冒充已通过。
