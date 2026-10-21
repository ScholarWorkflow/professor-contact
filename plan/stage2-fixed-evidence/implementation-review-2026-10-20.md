# Stage 2 U1 实现符合性审核记录（2026-10-20）

- 审核角色：项目自定义 agent `implementation_reviewer`（只读；不修改文件、不运行测试、不提交或推送）。
- 有效计划：`plan/stage2-fixed-evidence/implementation-plan.md` r3；测试范围：`plan/stage2-fixed-evidence/test-plan.md` t1。
- 首次审核版本：产品/测试实现 `2b813fc`（审核期间 HEAD 前进到 `f7ba548`，产品代码未变）。
- 首次结论：**部分完成**。

## 首次审核发现

### IR-U1-1（产品实现，需修复）

- 依据：计划 r3 §3.1.1/§3.1.3/§3.1.4；固定字段内显式 `zotero://select/library/items/<key>` 属于已声明引用，缺可信题名必须在写盘前失败。
- 偏差：renderer 只保护 `https?://` 与 Markdown 链接，裸 Zotero URI 未受保护。已声明的 key 会被替换进 URI 内部形成畸形/嵌套链接；未声明或无可信记录的裸 URI 会被静默保留。
- 最小修正：保护所有 URL 区间；把裸 Zotero item URI 按显式引用重绘为题名+原 URI，缺题名走既有 `missing_paper_reference_title`。不改 CLI/schema。

### IR-U1-2（测试证据适用性，待核实）

- 依据：测试计划 §2 U1-F「正文含来源分隔字样的实际修改确认并非整行或泛分隔符忽略」。
- 偏差：原用例在记录 pass 后直接改来源行，finalize 会先在旧 validator 绑定处失败；无法区分“只忽略生成时间”与“整行忽略”。
- 处理：由测试计划 owner/本地测试工程师在不新增必测项的前提下加强同一场景的隔离性。

## 修复与复核

- 修复提交：`3d6c2bc`（`fix(stage2): treat bare Zotero item URIs as explicit citations`），产品代码只改 `_stage2_render.py`，测试只改 `test_stage2_fixed_evidence.py`。
- IR-U1-1：新增 `STAGE2_ZOTERO_ITEM_RE` 与 `convert_segment`；裸 URI 有可信题名时重绘、缺题名时写盘前失败；所有 URL 区间不再进入裸 key 替换。U1-A 增加裸 URI 链接断言（7 个正确链接），U1-B 对 Markdown 链接与裸 URI 两种形态分别验证失败且不写文件。
- IR-U1-2：U1-F 用例改为移除旧 validator、把机器头/cache/ownership 绑定到修改后的正文，仅把顶部来源行“全文级 2 篇”改成“9 篇”；断言 finalize 后正文恢复“2 篇”且不含“9 篇”。这样可实现“整行忽略则保留 9 篇”的反例。
- 复核结论：**IR-U1-1 关闭、IR-U1-2 关闭，未发现新问题**；就这两项及直接影响而言实现符合性为完整。复核不重开整轮、不重跑测试，只采用已有执行记录；不代表计划、测试或合并关口批准。

## 复核后的待补与去向

- 本地执行工程师已在 `test-plan.md` §7 回填 `3d6c2bc` 的六项、相关既有检查与全仓回归结果及日志路径。
- 测试计划正式关口由测试计划负责人给出；合并按 `Merge Reviewer Rule.md` 单独审核。
