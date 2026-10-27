# 轻量 handoff 正文 future-work 接线 — 执行计划

- Requirement revision: 用户 2026-10-26 05:05 UTC：提交 paper-analysis 与 professor-contact 两个普通审核 PR，准备双计划；允许从已读按页正文补作者明确 future work，本地核验页码/原文，不因没有候选 ID 拒收。
- Revision: CONTACT-SOURCE-EP1.1；Proposed review status: pending。本 PR 仅双计划，不实现、不测试、不快合。
- Baseline: `18fd48d1b6f2e26241c304d6acddb025297f08e4` main；已核对 paper-analysis master `7b086ef361db54e2d3f6e333145a750ff56a48dc`。
- 唯一测试计划：[test-plan.md](test-plan.md)。配套上游计划：paper-analysis `plan/handoff-source-evidence/`。
- 规则：[Plan Reviewer](https://app.notion.com/p/3e80101a85f3817a94cbc6eca1a76a5c)、[Test Engineer](https://app.notion.com/p/3d80101a85f380d8a8f5ce528141e253)、[Consensus](https://app.notion.com/p/3d60101a85f3815a8c43f271f2b4d91d)。

## 1. 固定事实、因果与 owner

以下 contact 路径固定于 baseline，均位于 `.apm/skills/professor-contact/scripts/`：

- `stage2_chatgpt_handoff.py` 为真实入口，覆盖 `_stage2_chatgpt_handoff_impl.py` 的 hooks；`_instructions` 明文禁止已安装 agent 的正文选句能力扩大候选集；`_build_manifest/_verify_manifest_integrity` 只承认 exact-items-v1 / ocr-excerpt-v1；`_finalize_future_work` 向 validate/finalize 传仅含候选的 candidates.json，OCR 合并后也剥离完整 prepare。这是当前阻断点。
- 上游 `future_work.py` 的 SourceLocator 已支持完整 prepare.source_pages、质量/页码/连续原文校验；CLI 的 `--candidates` 能接受 prepare.json，`finalize` 核对其 PDF SHA。无需开发另一套原文校验器。
- `_stage2_handoff_text.py::prepare_text` 能从 prepare、同源缓存、旧 prepare 的 extract fallback 取得完整运输文本，但不会把该最终文字同步成供 future-work 使用的完整 prepare；所以只改 import 参数还不够。
- `_impl` 的 build 原位 hash PDF、上传无 PDF；import 绑定当前 local record、source/transport hash、本地 baseline 与 writer guard，facts 由同一安装 helper 基于原 PDF finalize。这些行为保持。
- Nix baseline 的 paper-analysis 锁定 `c140658cc60f9d9c3d17008cbab0b599f40c8e46`；已读取该 revision 的 future_work.py，包含 SourceLocator 正文接口，因此此次不预设必须更新锁文件。APM 调用仍使用显式提供的同一安装 skill/helper；用户自定义 override 的旧版本不能凭 master 状态当作已升级。

实际只读样本：样本 A 的 prepare 含 `source_pages`，候选页为 4/27/28/29，正文第 24–25 页有作者明示的后续研究；样本 B 的旧 prepare 缺少 `source_pages`，候选页为 16–18，正文第 15 页有作者明示的后续研究。未运行本地 PDF 校验，也未重跑模型；只确认候选遗漏与准备材料差异。私人原文与批次结果不入 Git。

因果链：运输说明及导入将候选封闭 → 新包声明正文证据契约并携带与运输原文一致的完整同源 prepare → 原分析角色从正文给完整引文/物理页 → 原 helper 本地核验 → 正式 sidecar/facts 可以包含候选外真实引文。

## 2. 最小公共契约

新就绪的 PDF 轻量 job 使用 `future_work.selection_contract: source-items-v1`。保留 bundle/result schema=1、carrier=pdf/source_mode=local、expected.future_work/facts、原 input_sha256、prepare/candidates/transport 各自 hash 及既有身份计算。selection_contract 已在 job_id/source_fingerprint 输入内，因此新契约产生不同 handoff 身份，不改写旧包。

返回文件仍为 `future_work_items.json`，形状 `{"items":[{"quote":"完整原话","translation_zh":"翻译","source":"章节","page":15}]}`；id 可省略，由 helper 生成/校验。页码为 1-based 物理 PDF 起始页；至多沿用上游一处相邻两页连续接缝，不新增字段、模糊匹配或任意跨页拼接。候选只帮助优先阅读，作者意图/一至两句完整语义由已有内容角色判断；不额外读整篇、不增加分析角色。确实没有作者明示可返回空 items；文字缺失/不可核验只能报告未完成。

旧 exact-items-v1 与 ocr-excerpt-v1 完整保留旧语义/文件/合并和唯一 excerpt 绑定；旧 candidate ID 可省略规则及合法 ID 不变。新 importer 根据已校验 manifest 分支，不根据外部 result 自报升级。已有旧包与结果不自动改写、补摘要或重新分析；如用户要补历史结果，须另行限定任务。

## 3. 实施变化与顺序

### A. 本地准备统一为一份完整证据

修改 `_stage2_handoff_text.py` 与 `_impl.build_bundle` 的接线，先获得本次 canonical prepared，再从它生成 paper.txt、配套 candidates.json 和 manifest hashes：

1. 原 job 的 prepare/candidates 及源 PDF SHA/一致性检查继续；只操作独立临时工作副本，不覆盖调用者输入。完整同源 `source_pages/page_quality` 已存在则复用。
2. 旧 prepare 无 source_pages 时，使用同一安装的 `future_work.py prepare <原 PDF> --debug-dir <本次临时目录>` 一次生成新版完整 prepare，仍通过上游统一 PDF 依赖，不自造 OCR/提取器，不复制 PDF。新版与原 job 的 PDF SHA 必须一致；同源有效页级缓存按现有 `pdf_runtime.py validate-ocr-cache` 复用。
3. 运输文字与证据共用该 prepare.source_pages。普通可读页保留 prepare 原文字；坏页仅采用同源校验通过的既有精确页 OCR，通过原 `merge-ocr` 更新 prepare（包含 required 页与实际使用额外坏页，保留已解决状态）。已有完整缓存只在通过现有 fingerprint 校验和物理页解析后，可给对应坏页提供精确页文字，再经同一 merge；不让另一份全文缓存独立覆盖运输文本而证据仍是旧提取。
4. required/必要坏页仍未解决时，沿用 upload_ready=false + text_preparation 的具体页面/原因及可用 local record；不自动 OCR、不上传 PDF、不静默退回仅候选新包。既有允许的非 required 空页保留缺页标记，不能成为引用证据。helper 太旧或准备失败同样明确未就绪。
5. 将 canonical prepared 与其 candidates 作为新包实际 evidence 文件计算 hash；纸本文本直接从这份 source_pages 生成物理页标记。不改旧输入 JSON，不把临时路径写入 portable manifest。原 PDF 仍在原路径算 SHA；新契约不允许任何 PDF 复制到临时目录、bundle 或 ZIP。

### B. 声明与导入

1. `stage2_chatgpt_handoff.py::_build_manifest/_verify_manifest_integrity` 明确允许 source-items-v1 仅用于 source_mode=local、有 text_transport、required 页已解决的 PDF job；旧两个 contract 按原逻辑验。未知 contract 拒绝。
2. 新分支 `_finalize_future_work` 将 manifest-bound canonical prepare 传给现有 `validate` 和 `finalize --candidates`，并传原 input_sha256；核对 prepare.pdf_sha256 与该源身份一致，仍验证 input 原文件 hash 和 transport 文件 hash。禁止把返回包中的新 prepare/候选当权威证据，也不按返回 quote 修改 prepare。缺 items、错误页、改写原文、不可读页、hash 不符沿用现有 incomplete/invalid 错误与 per-job 不安装行为。
3. 旧分支的 exact/OCR 行为不改；新分支无需 future_work_selections/excerpt 猜候选。相同合法候选继续由 helper 保留规范 quote/ID，facts 仍从本地生成 sidecar join，原安装事务/writer guard/baseline 防覆盖不变。
4. 更新唯一生成说明 `_instructions` 和 Codex/OpenCode analyzer 的 Step 4.5 A/C、相关 SKILL 简短说明：新 contract 从已读正文选择，web 不执行本地 helper、不请求不存在的 PDF 图片；旧协议只作旧包兼容说明。同两 runtime 的全局原则（baseline Codex 第34行限制 Conclusion/future work）和第701行“绝不从局限节找gap”等章节排除同步改为“可从任何已读正文选择作者明示待做事项；不得从局限性推断未明示计划”。保留 sidecar-first 与摘要证据边界，不凭章节名排除真实明示，也不扩大到读者建议。避免修改已废弃 `_impl._instructions` 而漏掉真实 wrapper。
5. 实施时仅在当前锁定 paper-analysis 缺所需能力或明确需要新说明时，更新该直接依赖到实际可用固定输出；不全量 flake update、不改 unrelated 依赖、不引用用户开发目录。上游文档 PR 可独立；contact 实现无需等文档 SHA 才使用已存在的正确 helper。

## 4. 取舍、影响和反例

选择复用现有 complete prepare 与 SourceLocator；替代方案“扩大关键词/末尾页或根据正文临时造候选”仍会遗漏/把语义变成程序猜测，不能解决根因；直接相信返回引文破坏原文约束，拒绝。

intended_change：新轻量包真实启用正文证据，旧 prepare 必要时正规补齐；preserved_behavior：原 source SHA、输入不可变、原位核验、旧两协议、facts关联、writer/baseline事务与其他 stages；approved_behavior_change：用户 05:05 批准的候选外原文接纳及相应跨仓接线；prohibited_side_effect：上传/临时复制 PDF、重跑总结、额外模型、开放无源 OCR-only 权限、批量改旧产物、全流程回归/新通用判定器。

关键反例及方案约束：运输缓存和 prepare 不一致由 A 的单一页源消除；旧 prepare 无全文由同源原 PDF prepare 补齐而非伪造；错误页/删字拼接由上游原校验拒绝；旧 result 不能把新 selection_contract 填回旧 manifest；源变化和并行本地编辑仍在既有 guard 失败，不能先安装后补核验。归一化后的 canonical prepared 只随新 manifest 发布，临时目录按现有生命周期清理。无新增身份系统或第二套事务。

完成双计划 review 后，产品实现者先改准备/manifest，再导入，再两 runtime/生成说明；测试工程师按唯一测试计划执行受影响目标，记录实际依赖 SHA 和结果。现在未实施/未执行，不自授批准或 PASS。

EP1.1：合并独立review指出的两 runtime全局章节白名单连带修改；T5原有说明一致性阅读覆盖，不增测试目标或入口。
