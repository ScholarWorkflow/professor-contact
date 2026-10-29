# 邮件 Markdown 支撑论文分析链接 — 执行计划

- Requirement revision: R1 (2026-10-29 用户要求邮件 md 链接支撑论文分析文件，并将本项独立 PR、双计划正常审核)。
- Plan revision: EP1。
- Target repository revision: `ad096fe31a4b5694cbe47a40f37b621435e1eeec`；分支 `feat/email-analysis-links`。
- 独立审核：2026-10-29 主代理审核 EP1 APPROVED，P1–P4 PASS；TP1 G1/G2 PASS。作者未自授批准。用户已明确授权本次三个 contact PR 必要产品、测试及计划修改；独立 G3 已通过（见 test-results.md）。
- 唯一测试计划：[test-plan.md](test-plan.md)。本次不包含中文译文、总览空格修复或 xdpool。

## 需求、证据及决策

规范依据：用户上述授权；同基线 [SKILL.md §论文引用链接约定](https://github.com/ScholarWorkflow/professor-contact/blob/ad096fe31a4b5694cbe47a40f37b621435e1eeec/.apm/skills/professor-contact/SKILL.md#L699-L706)：真实分析路径追加固定文案「分析」，以引用文档目录为基准；无路径仅 Zotero；发送正文不加链接。

事实依据（均同上述 SHA，描述现状而非新增需求）：
- `_contact_base.py::direction_papers` 从教授级唯一 `pack.papers[item_key]` 投影，`packages/professor-contact-codex/.apm/agents/professor-contact-analyzer.agent.md` 第 385、446 行约定 analysis_file 为绝对路径或 null。`canonical_index_path` 仅供规范化比较，并不证明写回事实包；本实现不依赖其写回。
- `_email_core.py::compile_email_entry` 的 papers/gaps 投影丢弃 analysis_file，Stage 5 无该事实；`contact_state.py::EMAIL_SOURCE_HASH_FIELDS` 已含 papers/gaps。
- `_stage5_email.py::render_source_table` 的 paper/later/gap 来源只展示标题；`render_fact_check_card` 仅 Zotero。
- `_stage5_commands.py` finalize 将来源表/事实卡仅写 md，txt 独立使用 Subject+body；输出均在教授目录。

决策及因果链：修复事实生产边界而非渲染时扫描文件 → Stage 4 从同一 pack 的 canonical paper 记录按 item_key 透传可选 analysis_file 到所选 papers 和 gaps → Stage 5 能将实际引用对应到真实本地分析文件 → 满足 md 可追溯而邮件正文不变。

替代方案：Stage 5 重读论文索引能补历史包，但引入第二事实源和发送阶段隐式重新发现；拒绝。旧包无字段按原行为正常渲染，新链接随正常 Stage 4 重编译取得，不强制批量迁移。

## 改动与接口

1. `_email_core.py`：为所选 paper/gap 投影添加可选 analysis_file，仅取既有 `pack.papers[item_key]` 或其同源投影。不接受模型 raw 自报路径；gap 即使不在最终 papers 选择中仍按 item_key 找真实记录。不存在字段则不添加，避免无路径旧数据无意义改变源 hash。现有 papers/gaps hash 自然涵盖新增事实，不改 hash 算法、不绕过陈旧判定。
2. `_stage5_email.py`：来源表取得输出目录（由命令层提供教授目录），对 paper/later/gap 来源追加同身份 Zotero 链接及可选 `｜[分析](<相对路径>)`；事实卡在原 Zotero 后同样追加可选分析链接。可局部共用格式化逻辑，但不新增公共框架。只使用存在的非空绝对路径字符串；未有/不合既有绝对路径契约时省略分析链接，不从 CWD 猜相对基准、不访问文件验证或重新解析论文。
3. `_stage5_commands.py`：仅为来源表传输出目录，不改 assemble/humanizer/发送 txt 路径。跟进来源表不新增论文内容；其既有事实卡沿用统一渲染。
4. `SKILL.md`：明确 Stage 4 透传、Stage 5 仅从邮件包补 md 内审链接及旧包兼容。仅适量更新当前来源/事实卡说明，不增加 validator 门槛。
5. 在既有 unittest 目录增加本改动的直接行为检查，复用现有 fixtures/runner；详见测试计划。

## 保持、边界与风险

- 保持 paper 身份、方向联合、选纸数量/顺序、gap 状态和 redlines，不改变模型提示/日文措辞、发送 txt 或审批行为。
- 没有 analysis_file 保留 Zotero；不猜文件名、不扫 `_index.json`、不新增 analysis/linker/CLI/backfill。
- 正常路径含空格/中文/日文以尖括号表达；不在本 PR 扩展所有 Markdown 特殊字符转义或全仓修复。
- 原始路径若迁移后失效，仍是既有事实所指，不伪称已实测文件可达；不新建文件存在性认证。
- 新编译包中路径变动自然改变 source_hash；历史包无字段仍可用但不会自动补链。仅受影响邮件按原流程重编译，不重跑无关业务。
- 尚无需用户决定的产品边界；若源事实实际不符合绝对路径契约，先据实报告而非猜测。

## 实施与审核顺序

EP1 与 TP1 固定后独立审核；批准后实施上述最小范围，执行批准的定向检查，记录命令/版本/实际结果供 G3；再独立完整 diff 合并审核。新分支正常提交、Draft PR，不 force、不自动 merge。若路径/所有权决策变化，修订唯一正文并仅重审受影响关口。文档 SHA 改变不触发业务重测。

规则：Project Consensus `3d60101a85f3815a8c43f271f2b4d91d`；Plan Reviewer Rule `3e80101a85f3817a94cbc6eca1a76a5c`；Test Engineer Rule `3d80101a85f380d8a8f5ce528141e253`。独立审核记录应包含 P1–P4 和 completeness；本次独立审核 P1–P4 PASS，EP1 APPROVED；实施候选 `1834ffdd8e9dc1d027db0d30a204f5993cb32633` 的源码 M1–M3 通过，无缺陷；TP1 G3 PASS。仅整理此审核记录不重跑。
