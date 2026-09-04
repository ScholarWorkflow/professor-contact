---
name: professor-contact
description: 处理日本大学院程序的「套磁」工作流（runner 版）。Stage 0 从 professor-topic-clustering 的 normalized 方向预筛.json 交互选择方向并写 `教授研究/套磁目标.json`（不再使用 Zotero 固定标题「套磁候选」note，无 Stage 0 Markdown）；Stage 1 由 `contact_stage1.py` 按被选方向构建保守高召回候选快照 `教授研究/套磁阶段1候选.json`（候选按方向独立、只做廉价证据扩召、绝不宣称最终归属），并只对缺失 PDF 的候选 item key 走 `professor-collector(pdf_only, item_keys=…)` item 级定向补下（全部就绪即 no-op）；Stage 2 只消费该机器状态与候选集。阶段 2--5 由本地确定性 runner `contact_state.py` 分担缓存、范围选择与输入包：阶段 2 产出 `套磁候选输入.json`（阶段 3 唯一事实源；gap 池只来自有效 sidecar，`gap_scope`/`freshness_scope` 控制，freshness 逐 gap 缓存于 `_freshness_cache.json`）；阶段 3 产出 `套磁候选状态.json`（`refresh_scope` 控制，只读输入包不读 Markdown）；阶段 4 由 runner 校验指纹后写 `套磁选择.json` + 编译程序级 `邮件输入.json`（精确 item_key+gap_id join，阶段 5 唯一事实源）；阶段 5 由 runner 拼装渲染邮件（送信前核对表/来源表/事实核对卡/humanizer 保护串）。受管 Markdown 带 `managed_by: contact_state` frontmatter，人手改动返回 `needs_decision`。future-work 证据仍 sidecar-first（paper-analysis gap-only 链不变），不降低任何事实核验/时效/人工确认要求。
metadata:
  version: 2.2.0
---

# professor-contact (skill — caller convention)

This skill is the **caller convention** for the 套磁 workflow (套磁 = contacting a Japanese professor before/around applying). The skill itself does NOT scan Zotero, download PDFs, or analyze papers — it tells you how to spawn the subagents that do.

> **skill = how to call (this file). subagent = the isolated execution unit (where it runs).**

## What this is for

After the screening pipeline (professor-collector `skip_pdf` → professor-topic-clustering `preview` → user picks keep-list → `pdf_only` → full clustering), the user may decide that **a specific direction of a specific professor** is worth contacting (套磁). Stage 0 presents the normalized preview directions（`方向预筛.json`）interactively, the user selects one or more directions (with optional per-direction user notes), and the selection is persisted to `教授研究/套磁目标.json`. The workflow no longer uses a fixed-title Zotero note as its selection UI. This skill's stages consume that machine state and turn it into 套磁 materials:

```text
professor-topic-clustering(preview:true)
    -> normalized 方向预筛.json
    -> Stage 0 interactive selection
    -> 教授研究/套磁目标.json
    -> Stage 1 direction-scoped candidate snapshot + targeted PDF fill
    -> Stage 2 evidence analysis
    -> Stage 3 ideas
    -> Stage 4 user selection
    -> Stage 5 email
```

`套磁目标.json` is machine state. There is **no Stage 0 human-facing Markdown output**.

## Prerequisite

For every professor the user may contact, run `professor-topic-clustering(preview:true)` using the current normalized preview contract. Each `方向预筛.json` must contain:

- `preview_fingerprint` + `preview_fingerprint_version`;
- stable `direction_id` per direction;
- complete `members[]` with `item_key` and preview confidence;
- `representatives[]` as a human-facing subset;
- names/summary and evidence coverage metadata;
- `membership_mode: overlap_allowed`.

Stage 0 does not require Zotero to be open. Later stages may still use Zotero as a paper metadata/PDF store, but never as contact-target state.

## Stage 0 selection contract（替代旧「标记约定」）

- **选择入口**：不再在 Zotero GUI 里建任何 note。用户在 Stage 0 的交互提问里选定方向（可多选），并可对每个方向写一段可选 `user_note`——理由 + 你的想法草稿/方向说明（「我本来就想做 xxx」的 xxx，你自己先写，阶段 3 会读它做修正）。写的越多，阶段 3 的修正越贴合你的真实想法；不写则退回纯模型生成候选。
- **机器 ID**：交互界面里的 A/B/C 展示标签不是身份；机器身份是稳定 `direction_id`。
- **多方向独立**：两个被选方向即使共享论文也保持独立（各自 `direction_id`/`members[]`/`member_fingerprint`/names/summary/user_note）；Stage 2 会按教授、按 `item_key` 去重昂贵工作并复用结果，但**绝不因此合并方向**。
- **修订**：对同一教授重跑 Stage 0 = 修订该教授的选择，不影响其他教授；仍被选方向的 note 保留，除非该方向的 key 出现在 selection `notes` 里——省略 key = 保留旧 note，key 出现即替换（显式传空串 = 清空）；先前的选择快照存 `selection_history`。
- **preview 变更**：target 新鲜度按**被选方向逐个判定**，整体 `preview_fingerprint` 只作 provenance/audit 元数据，不作为唯一有效性闸门：未选方向的新增/删除/改名/重聚类不影响已选 target；被选方向成员集合（`item_key`，即上游 `direction_id` 的推导依据）变化或方向消失 → Stage 1/2 以 `needs_refresh`（reason_code `preview_changed`，stale 条目精确到 `direction_id`）停止，须回 Stage 0 修订选择；成员集合不变时，`member_fingerprint` 变化（如 `preview_confidence` 升降）与 display 元数据（name/summary/representatives 等）变化一样只触发投影刷新——`resolve` 就地刷新该方向投影元数据并返回 `ok`（`user_note`、`selection_history`、选择本身不动），payload 以 `projection_refreshed` 标注。

## 阶段总览（每阶段 = 一个 subagent，可独立调用）

| 阶段 | subagent | 做什么 | 产物 |
|---|---|---|---|
| 0 | `professor-contact` | 读 normalized `方向预筛.json` → 交互选定方向（可多选 + per-direction user note） | `教授研究/套磁目标.json`（机器状态；无 Stage 0 Markdown） |
| 1 | `professor-contact-downloader` | 先 `contact_targets.py resolve`，再 `contact_stage1.py build` 构建逐方向候选快照（保守扩召 + 就绪检查），仅对缺失候选跑 `professor-collector(pdf_only, item_keys=<缺失 keys>)` 定向补下；全部就绪则 no-op | `教授研究/套磁阶段1候选.json`（机器状态）+ PDF 附件补下 |
| 2 | `professor-contact-analyzer` | 先 `contact_stage1.py verify` 校验 Stage 1 候选快照，以逐方向 `candidate_keys` 为读取/相关性/分析范围（可信度闸门只用 provisional members）；**full `paper-analysis` 覆盖候选集去重并集——每个 unique candidate 复用未变的有效 full analysis，否则跑一次 full pass（摘要级相关集与成本门只截断 gap/叙事，绝不截断 full analysis，issue #7 required flow #2）**→ 判定相关论文、署名、主线与 post-cost-gate 分析 scope 后，**总是先生成确定性的 ChatGPT handoff ZIP**。`chatgpt_handoff=continue` 时 ZIP 只是低成本 side effect，随后旧的本地 OCR/`paper-analysis` 路径语义不变；`wait` 时在任何新 OCR/`paper-analysis` 前软停止。提供匹配 result ZIP 后先严格本地导入成普通 analysis/sidecar，再继续既有 `stage2-resolve-plan → stage2-resolve-finalize → stage2-plan → stage2-finalize`（resolve 流水线对每个被选方向做权威性归属判定：移除误归类、新增他向支持、重命名、拆分/合并、写 `resolved_direction` 状态）。gap/runner/状态机仍完全本地 | `<教授名>/论文分析/_chatgpt_handoff/stage2-<id>.zip`（传输层）+ `<教授名>/论文分析/_resolved_directions.json`（方向权威归属）+ 原有 `<教授名>/套磁候选输入.json`（带 `resolved_directions` 字段，Stage 3 唯一事实源）/分析报告/_freshness_cache/index/sidecar |
| 3 | `professor-contact-idea-generator` | **只读输入包 + profile**（不读任何 Markdown/_index/sidecar）：`stage3-plan` 按 `refresh_scope` 生成逐方向候选 job → 模型写结构化候选 JSON（精确 gap 锚、done_by_self 只能【我的延伸】+差异点）→ `stage3-finalize` 校验后写状态并渲染候选文件；profile 改动只失效阶段 3/4，不失效阶段 2；白话校验结果另由 `stage3-record-validation` 写入独立字段 | `<教授名>/套磁候选状态.json` + `<教授名>/套磁想法候选.md` + `套磁想法候选总览.md`（后两者 runner 渲染） |
| 4 | `professor-contact-selection` | 用户从**候选状态**（非 Markdown）挑选 → `stage4-finalize` 校验指纹（过期 `needs_refresh` 不落盘）→ 写选择并**编译程序级邮件输入包**（精确 `item_key+gap_id` join；done_by_self 只作 extension_context_only） | `教授研究/套磁选择.json` + `教授研究/邮件输入.json`（阶段 5 唯一事实源，自包含短证据） |
| 5 | `professor-contact-email-generator` | **只读邮件输入包**（+profile/模板/info/boshu/`_contact_verify.json`）：默认生成首封和无回复跟进两种输出；`stage5-plan --mode both`（模型 job + 核验缓存检查）→ 送信前核验（5.9 不变）→ 模型只回首封的 4 句兴趣段+source_map+未来志向+学習中候选 → 用户补初次发送日期 → runner 同时拼装首封/跟进 → `humanizer-ja` 分别过稿；用 `--humanized-map` 一一对应，runner 先全量预校验再写盘 → `stage5-finalize --mode both`（保护串校验+渲染）→ validator 循环（validator 也只读 md+邮件包）并记录 `stage5-record-validation` | 每封选中邮件独立的 `套磁邮件.md`/`.txt` 与 `套磁跟进邮件.md`/`.txt`（单封用固定名，多封按方向与想法 ID 加后缀）+ `<教授名>/套磁邮件状态.json` + `套磁邮件总览.md` + `_contact_verify.json` |


## Stage 2 ChatGPT handoff（只替换逐论文高耗分析）

Stage 2 的 handoff 是**可选执行通道，不是第二套工作流**。`套磁候选输入.json` 仍是 Stage 3 唯一事实源，`contact_state.py stage2-plan/stage2-finalize`、gap/item/fingerprint 校验、Stage 3–5 全部保持本地权威。

### 启动时只问一次

- 完整 workflow **交互式**启动且调用方没有显式给 `chatgpt_handoff` 时，caller 必须在进入 Stage 2 前只问一次：
  1. `继续本地执行（仍生成 ChatGPT ZIP）` → `chatgpt_handoff=continue`
  2. `生成 ZIP 后暂停，等待 ChatGPT 结果` → `chatgpt_handoff=wait`
- 一旦选定，把该值原样传给 `professor-contact-analyzer`；**handoff 点不得再次提问**。
- 非交互/旧自动化没有该字段时固定按 `continue`，绝不因为升级后突然等待。
- 两种模式生成完全相同的逻辑 bundle；`continue` 不改变普通 Stage 2 结果语义，`wait` 不允许偷偷本地 OCR/`paper-analysis` 补齐。

### wait / resume

`wait` 在 analyzer 已完成方向可信度、署名、相关论文选择、成本门、幂等过滤与确定性 carrier/future-work prepare 后生成：

`<教授目录>/论文分析/_chatgpt_handoff/stage2-<handoff_id>.zip`

若确有待分析 jobs，analyzer 返回 `result=needs_external_result`、`reason_code=chatgpt_result_required`、`handoff_id`、`bundle_path`，这是软停止而非错误。零 jobs 时无需等待，继续普通 Stage 2。

用户把该 ZIP 交给 ChatGPT/外部处理并拿回 `stage2-<handoff_id>-result.zip` 后，重新调用同一教授的 Stage 2，并传 `chatgpt_handoff: wait` + `chatgpt_result: <result.zip绝对路径>`。analyzer **先按当前本地输入重新确定性构建 current bundle，再用 current bundle 校验 result**：因此 PDF/abstract/note/scope/local baseline 任一变化都会改变 handoff/source fingerprint，使旧 result 自动拒绝。匹配结果只会被安装到普通 `论文分析/...md`、本地 finalize 的 `.future_work.json`、经本地 `facts.py finalize` 验证落盘的 `.facts.json`（PDF fulltext job 必须带 facts 草稿；OCR-only/abstract-only job 显式无 facts 契约，不伪造、不本地补跑）与 `_index.json`；随后继续 sidecar/facts/`stage2-plan`/`stage2-finalize`，下游不因执行者来自 handoff 而分叉——本地与 handoff 两条路径产出同一规范化 paper-facts 形状。

外部 ZIP 永远不能直接提供权威 `_index.json`、`.future_work.json`、`.facts.json`、`套磁候选输入.json`、gap_id 或其它 Stage 3 状态；facts 草稿只有经本地确定性 `facts.py` 校验 finalize 后才成为 sidecar。多教授等待时每教授各有 bundle；恢复时用 `professors=<单个教授>` 逐个提交对应 result，避免错配。

## 目标状态语义（替代旧「标记语义」）

- **被选教授名单 = keep-list 信号**：Stage 1/2 先用 `contact_targets.py resolve` 解析被选目标，再把名单显式传给下游；Stage 1 的 PDF 补下走 item 级 fast path（见下），professor 级 keep-list 语义（清 `screened:"out"`、`include_deferred`）属于 Stage 0 之前的 pipeline 步骤，Stage 1 绝不重跑。
- **阶段 1 下载范围 = 方向候选集**：不再是「被选教授的全部可下论文」。Stage 1 先为每个被选方向构建保守高召回的候选集，再只对缺 PDF 的候选 item key 定向补下。

### Stage 1 方向候选集与定向补 PDF

对每个被选方向（候选集按方向独立，绝不因共享论文合并方向）：

1. **起点** = 该方向在 target state 中的完整 provisional members。
2. **廉价证据保守扩召**（只可用本地廉价证据，绝不当最终归属判定）至少覆盖：
   - 该方向的 low-confidence preview members（照常入选，额外记 `low_confidence_preview` 理由）；
   - 其他 preview 方向的成员与被选方向语义强重叠者（`cross_direction_overlap`，本地词面重叠证据 + `expansion_evidence` 记录）；
   - preview 未安置的论文（未分类/preview 后新增）中与被选方向有词面重叠者（`unclassified_or_new_since_preview`）；
   - 用户显式点名的论文（`user_named`，经 `--named-file` 传入，item key 或精确标题）。
3. **工作队列**：仅对「物理下载 + paper-analysis 补齐」把各方向候选 keys 并集去重；方向候选集本身保持分离。
4. **就绪检查**：按 `papers.json` 的 `pdf_status` 判定（`downloaded` = usable），已下载候选绝不重下。
5. **定向补下**：只把缺失的候选 item key 传给 item-scoped fast path：`professor-collector(pdf_only:true, item_keys=<缺失 keys>)`——不解析教授列表、不改 keep-list、不触发程序根级 collection 准备/打标。**绝不与 `professors` 同时传**。全部候选已就绪 → Stage 1 为 no-op，不 spawn collector。
6. **重跑幂等**：换网络后重跑同一流程，`papers.json` 状态未变的缺失候选自然重新入选重试。
7. **补下后刷新快照（强制）**：collector 会改 `papers.json`，downloader 在 collector 返回后必须重跑 `contact_stage1.py build`，以 post-fill 就绪状态作为最终快照与返回值——绝不留下描述补下前状态的 `套磁阶段1候选.json`（Stage 2 要 verify 消费它）。
8. **action 语义**：`noop` = 每个候选都已有 usable full text（missing 与 unresolved 皆空）；`pdf_fill_needed` = 有缺失可补候选；`needs_resolution` = 候选存在于 target/preview 但 `papers.json` 无条目（fast path 无法补）——返回 `partial` 并附诊断，绝不判成 `noop`。
9. **Stage 2 消费**：Stage 2 先 `contact_stage1.py verify` 校验快照对当前输入新鲜，再以逐方向 `candidate_keys` 作为读取/相关性/分析范围（`gap_scope=selected_direction` 的 gap 池同样来自候选集 sidecar）；**full `paper-analysis` 覆盖候选集去重并集，摘要级相关集与成本门只截断 gap/叙事，绝不截断 full analysis**；方向可信度闸门只用 provisional members，`relevance_reason` 附扩召理由，扩召候选绝不写成最终成员。

快照 `教授研究/套磁阶段1候选.json`（schema 1 / kind `professor-contact-stage1`）按教授持久化：逐方向 `direction_id`/provisional member keys/expanded candidate keys/逐篇 expansion reasons（+overlap evidence）/`input_fingerprint`/PDF readiness 汇总。`input_fingerprint` 是**精确依赖指纹**（v2），仅覆盖能改变候选成员/就绪状态的字段——被选方向身份与 provisional member item keys；被选方向词面画像输入（`name_ja`/`name_zh`/`summary_zh` + representative `title`/`title_zh`，供 `direction_profile_tokens()` 消费）；**全部** preview 方向的 membership placement 与 `preview_confidence`（cross-direction 门槛/low-confidence 理由/未安置判定由此派生）；Stage 1 实际读取的论文字段——`title`/`title_zh` 覆盖全部论文（扩召输入），`pdf_status` **仅对候选集**做指纹化（非候选论文的 pdf_status 变化不改变任何 Stage-2 input，绝不触发重建）。`preview_fingerprint` 仅作 provenance/audit 元数据保留，**不再是** Stage 1 有效性闸门——上游 `resolve` 会因 display-only 投影变化（如 `coverage_share`）合法改写 target 中的旧指纹，整 preview 指纹变化但精确依赖不变时 `verify` 仍 `ok`。`membership_claim` 恒为 `non_final_candidates_only`——**Stage 1 从不宣称最终方向归属**，候选集只是 Stage 2 的输入。无 Stage 1 人读 Markdown。

### Canonical target state

`<program_root>/教授研究/套磁目标.json` 为 schema 1 / kind `professor-contact-targets`，每个被选教授一个 target 对象，至少携带：

- professor identity 与教授目录；
- preview 路径、指纹与指纹版本；
- direction-ID 版本 / membership mode；
- 被选 `direction_id` 列表；
- 逐方向 provisional members 与 member fingerprint；
- 逐方向 representatives 与展示摘要；
- 逐方向 user note；
- 选择时间戳/历史（`selection_history`）。

**禁止手改此状态**，一律经 helper：

```bash
skillrepo exec professor-contact .apm/skills/professor-contact/scripts/contact_targets.py preview ...
skillrepo exec professor-contact .apm/skills/professor-contact/scripts/contact_targets.py select ...
skillrepo exec professor-contact .apm/skills/professor-contact/scripts/contact_targets.py resolve ...
```

## 确定性 runner 与状态文件

阶段 2–5 的可确定性工作由 `scripts/contact_state.py` 承担（纯本地：校验/指纹/缓存/排序/原子写/渲染；绝不启动模型、浏览器、Zotero、网络）。各阶段 agent 的循环统一为 **plan → 模型 job（只喂最小 `model_input`，模型落 result JSON）→ finalize（校验 + 原子写状态 + 确定性渲染）**；模型最终只回 `job_id/result_path/status/计数`。

### 单一机器事实源（Markdown 全是投影，禁止反向解析）

| 阶段 | 状态文件 | 位置 |
|---|---|---|
| 2 | `套磁候选输入.json`（方向事实包：支撑论文/gap shortlist 全证据/黑名单/版本关系/红线/user_note/narrative/输入指纹；含 `resolved_directions` 字段与每个 direction 的 `resolved_direction` 子字段；可含独立 `validator` 结果） | `<教授名>/` |
| 1 | `套磁阶段1候选.json`（逐方向候选集：provisional members/expanded candidates/逐篇 expansion reasons/preview+input 指纹/PDF readiness；`membership_claim: non_final_candidates_only`） | `教授研究/` |
| 2 | `_freshness_cache.json`（逐 gap：status + gap_fingerprint + candidate_fingerprint，无 TTL） | `<教授名>/论文分析/` |
| 2 | `_resolved_directions.json`（方向权威归属：resolved_direction_id/provisional_direction_id/name_ja/name_zh/resolution_type/papers_to_add/papers_to_remove/paper_justifications；`membership_claim: authoritative_fulltext_verified`） | `<教授名>/论文分析/` |
| 3 | `套磁候选状态.json`（候选 + profile 指纹 + 输入指纹；可含独立 `validator` 结果） | `<教授名>/` |
| 4 | `套磁选择.json` + `邮件输入.json`（自包含短证据，阶段 5 唯一事实源） | `教授研究/` |
| 5 | `套磁邮件状态.json`（逐 email：model_result/choices/render sha/validation；`issues` 必须为列表） | `<教授名>/` |

受管 Markdown（`套磁候选分析.md`/`套磁想法候选.md`/`套磁邮件.md`/`.txt`/两个总览）frontmatter 带 `managed_by: contact_state` + `state_fingerprint` + `render_sha256`。下次渲染发现人手修改 → `needs_decision / manual_markdown_changed`，不静默覆盖、不反向解析。可选决策：overwrite（覆盖为状态版本）/ keep_manual（保留手改但不作流程输入）/ promote（把要保留的内容经 `selection.note` 或 profile 正式写入状态后再渲染）。

### 范围参数

| 参数 | 阶段 | 取值 | 缺省 | 语义 |
|---|---|---|---|---|
| `gap_scope` | 2 | `relevant` / `selected_direction` / `all` | `selected_direction` | 只决定从哪些**已有有效 sidecar** 的论文选 gap；绝不触发额外 gap 提取 |
| `freshness_scope` | 2 | `shortlist` / `full` | `shortlist` | `shortlist` 只判断稳定排序的 5–10 条 gap；`full` 判断候选池全部。独立于 gap_scope 可单独扩大 |
| `refresh_scope` | 3 | `flagged` / `selected` / `all` | `flagged` | 只决定哪些方向（重新）生成候选；`flagged` 在 preview 工作流中=当前 Stage 2 输入包内的被选方向（旧参数名保留为兼容）；不调用阶段 2，不读 Zotero/sidecar/`_index.json`/Markdown |

### 缓存失效（稳定 reason_code）

所有 `needs_refresh` / `needs_scope_choice` / `degraded` / `needs_decision` 返回稳定 `reason_code`：`profile_changed`、`source_fingerprint_changed`、`missing_input_pack`、`missing_email_pack`、`missing_valid_sidecar`、`gap_status_unknown`、`manual_markdown_changed`、`shortlist_over_limit`、`result_missing`、`invalid_result_json`、`unknown_reference_id`、`blacklisted_gap_anchor`、`invalid_papers_override`、`duplicate_selection`、`duplicate_idea_id`、`duplicate_email_id`、`humanized_map_required`、`invalid_humanized_map`、`missing_user_choice`、`humanizer_violation`、`verify_stale` 等。给人读的 Markdown 只显示日常中文解释，不显示内部 hash。

阶段 2、3 白话校验结果分别用 `stage2-record-validation`、`stage3-record-validation` 写回各自状态文件的独立 `validator` 字段；不能覆盖阶段数据状态。阶段 5 使用 `stage5-record-validation`，其每条 `issues` 必须是列表，并保留原邮件的模型结果、用户选择、文件路径和 render SHA。

阶段 2 输入包失效条件（仅这些）：Stage 0 选择修订（方向被取消选择/换方向）、user_note 正文变化、方向成员集合变化、被选方向成员身份变化（成员 `item_key` 集合变化或方向消失，`needs_refresh` 阻断；未选方向变化、置信度/display 元数据漂移、整体指纹变化均不阻断，后者由 resolve 就地刷新投影元数据）、Stage 1 候选集（`candidate_keys` 参与 direction 指纹）变化、相关论文元数据/sidecar/freshness/版本关系/署名线变化、`force=true`。未变化直接复用包（不读论文全文、不重判 gap、不重写叙事）。freshness 缓存逐 gap 失效：任一相关后续论文的元数据/摘要/PDF/分析变化只影响受影响 gap。profile 改动只失效阶段 3 候选与阶段 4 选择/邮件包。

阶段 2 白话校验失败时，不能直接改受管 Markdown，也不能把普通 `stage2-finalize` 当作修订入口，因为相同输入指纹会命中旧叙事。原 facts 文件存在时，调用 `stage2-refine-plan --facts <facts.json> --validation-file <validation.json>`；原 facts 已过期或不存在时，调用 `stage2-refine-plan --professor-dir <教授目录> --validation-file <validation.json>`，runner 从已接受输入包做 pack-only 修订。两种路径都生成每个失败方向的短修订 job；模型只改 `narrative.positioning/gap_notes`，然后用对应的 `stage2-refine-finalize` 校验并重渲染。runner 只替换结构化叙事，freshness、gap、用户笔记和论文事实不变；成功后清除旧 validator 状态，需重新校验并最终调用 `stage2-record-validation`。全局红线中的 item key 由 runner 渲染为论文标题或“相关论文”，不进入人读正文。

### 版本关系（阶段 2 输入包内临时计算）

runner 在输入包内计算临时 `version_family/version_role/supersedes`：会议版/期刊扩展版仅在作者核心集合、题名/摘要主题、时间顺序、明确扩展证据（后续摘要正则命中 extend/journal version 等）都成立时合并（期刊扩展版为主证据，重复 gap 标 `suppressed_by`）；证据不足只写 `possible_family` 人工提示，不合并不压制不影响 freshness。

### Resolved directions（权威性方向归属，阶段 2 → 阶段 3–5 唯一方向身份）

preview 聚类以**摘要**为证据，可能把论文误放进 / 漏出某个方向；阶段 2 拿到全文级 paper-analysis facts 后，必须对每个被选方向做一次权威性归属判定，把结果写进 `<教授名>/论文分析/_resolved_directions.json` 与 `套磁候选输入.json` 的 `resolved_directions` 字段，阶段 3–5 只读这个状态，不再回读 provisional 身份或 Zotero 分类作方向归属。

**证据范围拆分（issue #7 required flow #2）**：full `paper-analysis` 的范围 = 全教授被选方向 `candidate_keys` 的去重并集——每个 unique candidate paper 复用未变的有效 full analysis，否则跑一次 full pass；摘要级 relevance 判定与成本门**只**决定相关集（gap/叙事/future-work 补齐范围），绝不截断 full analysis 或归属 resolution 的证据来源。resolved_direction 的逐方向指纹、resolve-plan 的 paper_evidence、split/merge/addition 检测全部以 candidate union 为准——被摘要判为不相关、但全文真正属于该方向的候选，必须能凭 full facts 被新增回来。

流水线（在 `stage2-plan/finalize` 之前必须完成）：

1. `contact_state.py stage2-resolve-plan --facts <facts>` —— 纯确定性零模型，读取现有 `_resolved_directions.json`：逐方向 `input_fingerprint` 仍匹配**且条目已 accepted** → `action=reuse` 不发 job；其余方向（含仍 pending 的提案）给出 `candidates.{additions,removals,splits,merges}` 列表与一个 `resolve:<教授>:<方向>` job。归属证据范围 = 全教授被选方向 candidate_keys 的去重并集（各方向 Stage 1 candidate 集可能不相交，跨 preview 误聚类的论文仍可被全文证据新增回来）；addition 候选按**全文证据分量**排序，provisional 成员/gap/authorship 先验不参与比较。
2. 模型按 job 写 `results/resolve-<方向>.json`：每方向 `resolved.{resolved_direction_id,provisional_direction_id,name_ja,name_zh,resolution_type,papers_to_add,papers_to_remove,paper_justifications,split_target,merge_target,user_note}`，resolution_type ∈ {`unchanged`/`renamed`/`split_from`/`merged_into`/`refined`}。result 与方向身份强绑定：`collection_key`/`provisional_direction_id` 必须等于 job 方向，非 split 的 `resolved_direction_id` 也必须相等（runner 拒绝任何漂移）。**split_from**：`split_target` = 全新子方向 ID（不得与现有方向冲突），`papers_to_add` = 移入新子方向的论文（源方向至少留 1 篇）；**merged_into**：`merge_target` = 本教授现有目标方向 ID，add/remove 必须为空。
3. `contact_state.py stage2-resolve-finalize --facts <facts> --results <results>` —— 校验 schema/合法性（identity 绑定、`papers_to_remove` ⊆ provisional member、`papers_to_add` ⊆ 教授级 candidate union、split/merge 结构约束、禁止 merge 链），并对任何 membership 变更（add/remove 及 split 移动的论文）逐篇校验当前 `facts_state=valid` —— abstract-only/legacy/证据链断裂的论文无法成为归属变更依据，违者 `invalid_result_json` fail closed；**结构性 material change 另有全文证据 gate**：`merged_into` 需通过 `_authoritative_merge_basis`（双方都有 facts-valid 论文且 topic terms 收敛；共享论文+画像重叠只是 detector hint，单独不构成权威 merge 依据），`renamed` 与无 membership 变更的 `refined` 要求方向内至少一篇当前 `facts_state=valid` 的论文——零全文证据时的 authoritative 身份/结构重构一律 fail closed（unchanged/provisional 不需要证据）；逐方向写 `input_fingerprint` 落 `_resolved_directions.json`。**acceptance 生命周期**：条目带 `acceptance` 字段，`unchanged` 直接 `accepted`；material change 写为 `proposed`——在用户选择之前只是提案：proposed 方向下一轮 plan 总是重新 process，resolve-finalize 无新 result 时原样保留提案并继续报 `needs_user_choice`，绝不把未接受的提案当已接受缓存。`needs_user_choice=true` 当且仅当存在未接受的 material change（已 accepted 的 resolution 重跑不重复提示）。全部方向 reuse 时可跳过 2–3 直接进 5。
4. **有 material change 时**问用户采纳 refined / 回 Stage 0 重选 / **沿用 provisional**。沿用 provisional 也是明确的 resolution 决定，必须持久化而不是省略 resolved 文件：对用户选择保留的方向重跑 `stage2-resolve-finalize --keep-provisional <ckey1,ckey2>`（零模型；条目改写为 `acceptance=accepted`、`decision=user_kept_provisional`、resolution_type=unchanged、名字/成员 = provisional，取代该方向旧提案），随后照常带 `--resolved-directions` 跑 stage2-finalize——每个方向仍都有显式 `resolved_direction`（下游无需 provisional fallback），且该决定被复用：facts/profile/candidate union 不变时不再重发 resolve job、不再重复提问，只有 v4 fingerprint 变化才重新提示。不选 → 保留旧产物 + `needs_input`。**稳定 resolved ID 策略**：resolved ID 是用户确认过的稳定标识；fingerprint 变化后 re-resolve 若为同一概念 split 提出不同 `split_target`，新 ID 只是新的 material proposal 走用户确认（validator 只要求不冲突，绝不静默替换已物化 child），未采纳前输入包保留旧 child——不要把 prior accepted 身份塞进 resolve model_input 换取「ID 延续」，那会让 fingerprint 依赖自己盖章的输出导致 reuse 无法收敛。
5. `stage2-finalize --resolved-directions <path>` —— 对 sidecar **fail closed**（schema/kind/professor 不符或任一方向 fingerprint 过期 → `resolved_directions_stale` / `resolved_directions_professor_mismatch`，绝不静默应用）。校验通过后应用 resolved 状态：移除/新增论文、刷新 `name_ja/name_zh`；**split_from 在输入包创建真正的第二个权威方向条目**（split 论文与 gap 引用迁移；全文救回但不在 `relevant_keys` 的 candidate 由 runner 直接从库+facts 物化进子方向，Stage 3 对两个方向分别生成 job）；**merged_into 把源方向条目从输入包移除**（论文/gap 引用完整移植到目标并记 `merged_from`，根部索引永久保留 源→目标 映射）；**每个方向（含 unchanged）都写入 `resolved_direction` 子字段**（权威 resolved ID）。**应用成功即用户接受**：runner 把 sidecar 条目标记 `acceptance=accepted`，此后重跑不再提示。已物化的 split 子方向在后续无变化 reuse finalize 时原样保留（不被已裁剪的源方向重建为空）；源方向因 facts 变化重新构建时子方向随新 resolve 结果重建。

复用与失效：

- resolved 状态不是 paper-analysis 的二级缓存，而是独立的方向归属机器事实。复用条件 = 逐方向 `input_fingerprint` 与本轮仍匹配**且 `acceptance=accepted`**。fingerprint（version 4）= 该方向 resolve job **规范化 model_input 的 SHA**（`_build_resolve_model_input` 同时用于发 job 与算指纹，二者按构造一致）：教授级 selected candidate union 每篇论文的 metadata + **有效** `facts_state`/`facts_error`/topic terms（future-work sidecar 精确 join 是证据链一部分，join 断裂会改变所有看到该论文的方向）+ 对**全部**方向的 affinity 分数；跨方向 removal/split/merge/addition 候选证据（依赖他方向画像/membership/gap）；本方向画像（credibility/user_note/provisional 成员）与 gap evidence；resolve 规则文本。因此其他方向的 profile 或 facts 有效性变化同样失效本方向缓存（跨 preview 误聚类修正不被缓存挡住）；而 analysis Markdown 正文、abstract/month 等不进入 job 输入的内容**不**失效缓存（编辑性改动不烧 resolve job）。
- 一篇论文可支撑多个 resolved 方向（共享 membership 仍然合法）；同一论文 analysis 仍按 `item_key` 去重执行一次。
- keyword/grep 单独命中不构成 resolved membership 证据——必须全文 facts 支撑。
- 下游（阶段 3 / 4 / 5）不再回读 Stage 1 候选快照 / target state `members[]` / Zotero 分类作方向归属；如需重置，必须清掉 `_resolved_directions.json` 并重跑 resolve 流水线。

### 迁移（migrate-v3）

```bash
python3 scripts/contact_state.py migrate-v3 --plan --program-root <程序根> [--out plan.json]
python3 scripts/contact_state.py migrate-v3 --apply <plan.json> --program-root <程序根>
```

`--plan` 只读旧产物、输出迁移计划（不调模型）：方向分为 `ready`（schema 2 index + 有效 sidecar + 精确 gap ID + 足够元数据）/ `needs_stage2`（缺 sidecar/时效/精确 ID/相关论文事实）/ `needs_stage3`（输入包可迁移但候选无可恢复机器元数据）/ `blocked`（损坏/来源矛盾）。`--apply` 仅对 `ready` 做无模型、无网络、无 token 的确定性迁移（写输入包 + freshness 缓存，标 `migrated: true`，不渲染 Markdown、不隐式启动阶段 2/3）；其余输出最小补跑清单。

## 阶段 5 — 套磁邮件（核心设计约定）

阶段 5 把阶段 4 选定的想法变成一封首封日语套磁邮件，并可同时生成一封数日后无回复时使用的跟进邮件。以下约定是 caller 与 `professor-contact-email-generator` 共同遵守的设计共识。

### 5.1 只产兴趣段 + 未来志向句 + 学習中候选

整封邮件里**由模型创作的内容 = 核心兴趣段（4 句强制四动作） + 未来志向句（1 句） + 学習中候选（2-3 个供挑）**。其余全部是模板固定文本 + 占位符填充。模型不得改写模板固定段落（寒暄/自我介绍/资历框架/请求/收尾）。

兴趣段四句结构（**全部必有**，按下列结构生成）：
- **①自定位句**：句式「**〈用户角色〉として、私はこれまで、〈领域信念〉と考えてきました**」。用户角色 = 用户与该领域的真实使用关系（软件工具用户 / 音乐・视频 App 用户），**非职业背景**；领域信念 = 领域内"希望这门技术更好"的日常愿望，**必须通过防假检验**；用户技术背景挪去资历段。
- **②点名+桥接句**（1-3 篇）：从选中想法 `papers[]` 挑（锚定词/年份新/被红线点名不作主点名，规则不变）；桥接 = 跨论文共同主题的应用级表述（「…を拝読し、<共同主题>に気づかされました」），**共同主题须对每篇被点名论文成立（自检），不成立的剔除、宁少勿混**；疑似幻觉/勉强方向只信被点名论文的共同主题，不借用方向定位。
- **③宽泛例子句**：一句 if-then 应用场景；**锚点优先教授自己写过的假设/future work**（从分析.md 的「可延伸方向」节/方向定位叙事找软层表述，措辞贴近教授原话），无可锚软层退回 idea_zh 投射。**锚点时效限定**：只锚 `gap_status ∈ {open, partial, unknown}` 的条目——`done_by_self`（教授后续论文已做掉，分析.md「已被本人实现」小节）禁锚；`partial` 锚落剩余缺口。
- **④软收束句**：模板固定「このような<领域名词>は、まだ数多く存在すると感じております。」，领域名词参数化，不展开。

**分层原则**：兴趣段只写软层（是什么 / 教授自己写的话 / 用户意图）；「怎么做」层（方法/贡献/指标/数据集/年份叙事）一律不进邮件，留在 套磁候选分析.md / 论文分析 / 套磁想法候选.md 作面试预答。**排除清单**：禁方法名/模型名/算法名（标题内除外）、指标数字、数据集名、组件名、公式、限定语链、年份叙事；允许标题原文、应用场景词、自定位。**整段软上限 ≤180 字**。

**夸+启发、不找碴（邮件基调）**：对教授研究的表述只有两种合法形态——**夸**（②中具体到论文+共同主题的"读到什么/看到什么可能"，禁「久仰大名」「贵方向优秀」式空洞夸；①自定位禁恭维语）与**启发**（③中引用教授原话的假设/future work + "我愿在此方向探索"，措辞简单、短、不堆修饰）。**找碴判定（双过才合法）**：措辞主体是"我"（"我想/我受启发/我愿探索"，不是"教授/您的 X 不足/没考虑/应改进"）AND 延伸点属作者明说的 future work（教授 future work 原话，非读者推断）——缺一即找碴，blocking。validator 规则 9 兜底。**内部材料（阶段 2/3 分析、候选）不套此禁令**——它们可尖锐（方向可信度、future work 判断是决策材料），找碴禁令只管对外邮件文本。

**未来志向句**（兴趣段下一段「将来的には……に携わる研究や開発を行いたい」的指定语）：模板骨架固定为 `先生のご指導のもとで関連分野を深く学び、将来的には{{未来志向}}に携わる研究や開発を行いたいと考えております。`，其中 `{{未来志向}}` 由模型按该方向写——把 idea_zh 的增量落点 + 用户背景技能（profile）映射成该方向下的未来工作表述，**宽泛方向表述 + 背景技能（设计/实现/评估/实数据适用），禁具体技术栈**（模型名/算法名/框架名/组件名）。**绝不能用成功模板里属于另一个方向的那句套话**；同样遵守红线（可行可追溯）。

**学習中句**（資历段「現在は……にも積極的に取り組んでおります」的指定语，如「機械学习的基础知识」）：模板骨架固定，指定语由模型按该方向给出 **2-3 个候选**（名词短语，措辞必须贴近用户 profile 中明确的知识储备），**交用户对照自己的知识储备挑选**。候选不是"我已在学"的断言，而是"为该方向想补的知识"；用户不挑不能擅自写入。真实性锚 = 套磁信息.md「当前在学的知识」字段（空则由用户挑选后回填）。

### 5.2 模板：内嵌黄金骨架 + 可覆盖

- **黄金骨架**：抬头（大学/研究科/先生名）→ 寒暄 → 自我介绍 → 入学目的 → `{{兴趣段}}` → 愿望 → 资历 → 志望 → 附件 → 收尾。默认内嵌在 subagent 中。
- **可覆盖**：首封使用 `套磁邮件/套磁模板.md`；跟进使用 `套磁邮件/套磁跟进模板.md`。两个文件都可用 `{{}}` 占位符覆盖；缺文件时分别使用内嵌骨架。
- **首封占位符**：`{{subject}}` `{{大学}}` `{{研究科}}` `{{専攻}}` `{{先生名}}` `{{出身校}}` `{{氏名}}` `{{入学年度}}` `{{入学月}}` `{{学位}}` `{{入試批次}}` `{{兴趣段}}` `{{未来志向}}` `{{学習中}}` `{{志望}}`。
- **跟进占位符**：`{{先生名}}` `{{大学}}` `{{研究科}}` `{{学位}}` `{{入学年度}}` `{{入学月}}` `{{出身校}}` `{{氏名}}` `{{初回送信日}}` `{{研究主题}}` `{{メールアドレス}}`。跟进 Subject 默认是首封 Subject 前加 `Re:`。
- **填充来源**：大学/研究科/入学年度/入学月 ← info.json；専攻/学位/入試批次 ← boshu_analysis.json exam_type；先生名 ← selection.json professor；出身校 ← 套磁信息.md（缺省「総合大学出身」）；氏名 ← 交互补齐；兴趣段/未来志向 ← 模型按方向生成；学習中 ← 候选交用户挑（真实锚 = 套磁信息.md「当前在学的知识」）。

### 5.3 Subject 构造

- 默认 `【入学希望】{{入学年度}}年{{入学月}}期 {{学位}}{{入試批次}}入学に関するご相談`
- **`{{学位}}` 优先从要项读**：`boshu_analysis.json` `exam_type.degree`（如「博士前期課程」）；读不到退回「大学院修士課程」（用户旧格式）。
- **`{{入試批次}}`**：从 `exam_type.selection_name`/source 提取批次词（冬季/夏季/2次募集/3次募集/海外特別入試）；提取不到为空。
- 模板 `{{subject}}` 若已被用户写死 → 用用户的。

### 5.4 红线硬约束

红线 = talking_points[] + selection note + 套磁候选分析.md 校准点 + mismatches。生成时作为**硬约束**消费：被红线限制的表述按红线改写（如「预测+缓解闭环」只能作衔接句不能当新点子；「不说教授已证明 X」；「不要引用未提供来源的实验数字」）。**宁短勿错**；压缩结果必须可回溯到来源。

### 5.5 身份表述与志望

- **身份表述以黄金邮件为基准**（具体经历以用户 profile 为准），profile 额外信息按需提，不加不必要细节（避免臃肿）。
- **志望默认非第一**：`{{志望}}` 默认「先生の研究室を志望として出願させていただきたく存じます」；只有确认该教授是唯一第一志愿（`first_choice` 或交互确认）才改「第一志望として」。

### 5.6 humanizer-ja 过稿（正文出稿前）

`professor-contact-email-generator` 在整封首信/跟进信拼装完成、交互字段（志望/署名/学習中候选/初次发送日期）回填后、写盘之前，加载 `skill(name: "humanizer-ja")`（模式固定 **business**）分别对两封邮件正文（Subject + 正文）过一遍：

- **目标范围**：首封重点处理模型创作的兴趣段/未来志向句；跟进重点处理模板中的重复、过度道歉和不自然连接——run-on 长段拆句拆段、文末「〜と考えております」等重复收束、抽象名词化、机械接续词堆叠。**同时巡查模板拼装造成的冗余**并合并——humanize 是唯一允许动模板拼装冗余的地方，合并处来源标注记 `[模板] 经 humanizer 合并`。
- **兴趣段①④不特殊保护**：四动作结构收尾各异（考えてきました / 気づかされました / といったことです / 感じております），天然不触发「重复收束」规则；若个别句真被识别为 AI 味则照常打磨，不做模板级保护。
- **硬边界**：不改事实/红线——首封论文标题、年份、TOEIC/N1/工作经历，以及跟进初次发送日期、学校、研究科、入学信息、研究方向、署名、附件说明一律原样；不补 profile 之外的新信息；不就 humanize 改动生成时的红线记录（红线在生成时已消费）。
- **用户选定项不动**：Step 交互回填的学習中候选、志望表述、署名等用户选择短语保持原样。
- **次序**：拼装+交互 → **过稿** → 写盘（产物）→ validator 校验（**校验对象 = humanizer 过稿后的最终文本**，validator 是最终关卡）。

### 5.7 校验循环

`professor-contact-email-validator` 只报告不重写，generator 循环最多 2 轮，仍 fail 保留第 2 轮产物记 problems。**输入契约：validator 只读 最终 `套磁邮件.md` + `邮件输入.json`（+md 内嵌核对表），不读候选/分析 Markdown、`_index.json`、sidecar、Zotero、网络**。校验项：
- blocking：首封兴趣段/未来志向句每句可回溯（**六类来源**：user_note / idea_zh / fit_note / 方向定位与研究脉络 / future work 与教授假设 / 论文标题原文；④软收束句为模板固定句免回溯）、无六类之外的新断言、论文标题与 selection papers[].title 一致、敬语/称呼正确（です/ます/先生）、学習中句来自候选集/用户自填（不擅自发明新领域）、无残留 `{{}}`、无未经标记的「第一志望」、**③锚定的 future work 非 done_by_self**（validator 规则 10）。跟进邮件另查首封关联、初次发送日期、主题一致、无新研究断言；跟进不要求重复四句兴趣段。
- **humanizer 例外**：5.6 过稿造成的措辞变化（run-on 拆句、文末重复收束、模板拼装冗余合并）不视为「模板被擅自改写」；validator 只盯事实是否被改（论文标题/年份/TOEIC/N1/工作经历等），纯润色不作 minor。
- 红线本身不自动校验（人话难形式化），生成时已消费。

### 5.8 产物

- `<教授名>/套磁邮件.md` / `.txt` — 阶段 5首封邮件；无回复版本为同目录的 `套磁跟进邮件.md` / `.txt`。两类文件都包含独立的送信前核对表、humanizer 保护校验和 validator 记录；跟进文件额外记录首封 email_id 与初次发送日期。
- `教授研究/套磁邮件总览.md` — 程序级聚合。
- 幂等：同方向重跑覆盖对应文件（受管 md 人手改动 → `needs_decision`）；`套磁邮件状态.json` 记录 render sha 与 validation 状态。
- **阶段 5 不需要 Zotero**（纯本地文件；论文标题已在阶段 2 从 Zotero 取过）。

### 5.9 送信前核验

阶段 5 在拼装邮件之前，对每位教授做一次「送信前核验」，结果以固定表格写进每封 套磁邮件.md（头部引言之后、正文之前），作为发信前最后人工过目的 checklist。设计约定如下：

- **核验范围（8 个固定项目）**：①收件邮箱＋来源阶梯级 ②教授在要项教员一览在册（学域/分野/职衔＋页码或 extraction 行）③目标批次存在性与名额（如「冬季 一般選抜 若干名」）④抬头逐字比对（{{大学}}/{{研究科}} vs 要项原文标题）⑤件名批次词 vs exam_type.selection_name ⑥日程快照（出願/試験/合格発表 ← boshu_analysis.json schedule[]）⑦内诺制度要点（受験承諾書/签名 ← inner_consent）⑧特记 ⚠（info.json notes 中记录的目标批次未实施等矛盾）。
- **三级结论**：`confirmed` / `not_found(⚠)` / `unverified`。not_found 不阻断生成，但 md 顶部打醒目警告横幅交用户决定；unverified 如实标注。
- **邮箱五级查找阶梯**（零成本→高成本）：①程序根缓存 ②论文分析记录 ③用户提供的官方教员主页 ④用户提供的研究室网站 ⑤全空 → unverified 并交互问用户。能凑齐两个独立来源就交叉验证。邮箱一律原样照抄来源，禁止按学校域名规律推构。
- **在册判定三规则**：姓名 NFKC 规范化＋去全部空白后全名精确匹配；不做姓氏-only 匹配；按邮件所在分类核对要项分野。
- **快照边界**：日程/内诺只读 boshu_analysis.json 已结构化字段（schedule[]/inner_consent，自带页码摘录），缺则标 unverified——**不为快照新增爬取**；要项没分析过的学校先补跑 boshu-analyzer。
- **缓存**：`<教授名>/_contact_verify.json`（各项目 verdict＋来源 URL＋时间戳＋info.json/boshu_analysis.json 指纹）。指纹变化、>30 天、或 force 才重核；命中即复用。核验是教授级的：同一教授多封邮件共享一份核验，但每封 md 各自内嵌完整核对表。
- **validator 联动**：校验规则新增两条（规则 11 抬头与核对表一致＋核对节存在；规则 12 核对表完备且 ⚠ 必须带横幅）——防止未来某次生成悄悄跳过核验。
- **范例**：公开文档只使用 `Professor Example`、`Fixture University A`、`faculty@example.edu` 和 `https://example.test/` 等合成值。

操作细节（阶梯步骤/缓存 schema/核对表模板）内嵌在 `professor-contact-email-generator` agent 定义中，本节为设计共识记录。

## 输入前提：profile 与 套磁邮件/ 配置目录

阶段 3/5 依赖你的研究兴趣/背景/想做的课题。写一个本地文件：

- **配置目录**：`<调用方工作目录>/套磁邮件/`（与程序目录同级）。里面放：
  - `套磁信息.md` — profile（研究兴趣、背景[出身校/专业/工作经历]、想做/正在想的课题方向、语言偏好）。
  - `套磁模板.md` — 可覆盖首封邮件模板（含 `{{}}` 占位符；不建则阶段 5 用内嵌黄金骨架）。
  - `套磁跟进模板.md` — 可覆盖无回复跟进模板（可选；不建则使用内嵌模板）。可用占位符：`{{先生名}}` `{{大学}}` `{{研究科}}` `{{学位}}` `{{入学年度}}` `{{入学月}}` `{{出身校}}` `{{氏名}}` `{{初回送信日}}` `{{研究主题}}` `{{メールアドレス}}`。
- **查找链**：`<调用方工作目录>/套磁邮件/套磁信息.md`（或 套磁模板.md）首选；subagent 找不到时向上搜 `<program_root>` 的 `../套磁邮件/`、`../../套磁邮件/`（最多 2 级）。

没写 profile → 阶段 3 只按论文内容生成想法、不做与用户真实兴趣的契合评估（并在报告注明）；阶段 5 缺字段（如姓名）交互补齐。

## How to call

Spawn the subagent via the Task tool (all are `hidden`, so the Task tool is the ONLY way):

```
# 阶段 0：交互选定套磁方向（读 方向预筛.json，写 套磁目标.json）
task(subagent_type: "professor-contact", prompt: "folder_path: <program-root or per-専攻 subfolder>\nprofessors: <可选，逗号分隔精确教授名>")

# 阶段 1：方向候选集 + 定向补 PDF（全部候选已有 PDF 时自动 no-op；默认只使用合法来源）
task(subagent_type: "professor-contact-downloader", prompt: "folder_path: <...>\nprofessors: <可选，逗号分隔精确教授名>\nnamed_papers_file: <可选，用户点名论文 JSON 绝对路径>")

# 阶段 2：分析（交互式 caller 已在此之前把 handoff 模式问好；非交互缺省 continue）
task(subagent_type: "professor-contact-analyzer", prompt: "folder_path: <...>\nprofessors: <可选，逗号分隔精确教授名>\nchatgpt_handoff: continue|wait（非交互缺省 continue）\nchatgpt_result: <匹配 result ZIP 绝对路径，可选，仅 resume>\npaper_analysis: relevant|all（可选，缺省 relevant）\ngap_scope: relevant|selected_direction|all（可选，缺省 selected_direction）\nfreshness_scope: shortlist|full（可选，缺省 shortlist）\nkb_import: true|false（可选，缺省 false）")

# 阶段 3：生成想法候选（refresh_scope 缺省 flagged=当前 Stage 2 输入包内被选方向）
task(subagent_type: "professor-contact-idea-generator", prompt: "folder_path: <...>\nprofile_path: <绝对路径，可选>\nrefresh_scope: flagged|selected|all（可选，缺省 flagged）\ncollection_key: <精确方向 key（=direction_id 兼容键），可选>")

# 阶段 4：记录选择
task(subagent_type: "professor-contact-selection", prompt: "folder_path: <...>\nselection: <可选，直接给选择，跳过交互>")

# 阶段 5：默认同时生成首封邮件和无回复跟进邮件
task(subagent_type: "professor-contact-email-generator", prompt: "folder_path: <...>")

# 只生成首封或单独补生成跟进
task(subagent_type: "professor-contact-email-generator", prompt: "folder_path: <...>\nmode: first|followup")
```

### Input contract（公共字段）

| Field | Required | Notes |
|---|---|---|
| `folder_path` | yes | 程序根（含 info.json）或 per-専攻 子文件夹。 |
| `profile_path` | no | profile 文件绝对路径；缺省自动向上搜 `套磁邮件/套磁信息.md`。 |
| `professors` | no | 限定只处理这些教授（逗号分隔 kanji 名）；缺省=处理 `套磁目标.json` 中全部被选目标。名单中的教授未被 Stage 0 选入 → resolver 返回 `professor_not_selected`（needs_input）。 |
| `named_papers_file` | no | 仅阶段 1：JSON 文件绝对路径，`{"directions": {"<direction_id>": ["<item_key 或精确标题>", ...]}}`，把用户显式点名的论文并入对应方向候选集（`user_named` 理由）。 |
| `paper_analysis` | no | 仅阶段 2：`relevant`（只跑相关论文——user_note 点名 ∪ 术语/语义匹配，缺省）或 `all`（方向全部成员论文，强制全量）。相关集 >10 篇时 analyzer 会先问确认。 |
| `gap_scope` | no | 仅阶段 2：gap 候选池范围（`selected_direction` 缺省）。只从已有有效 sidecar 的论文里选，绝不触发额外提取。 |
| `freshness_scope` | no | 仅阶段 2：`shortlist`（稳定排序 5–10 条，缺省）/ `full`（候选池全部）。 |
| `chatgpt_handoff` | no | 仅阶段 2：`continue` / `wait`。交互式完整 workflow 由 caller 在 Stage 2 前问一次；非交互省略固定等价 `continue`。两者都生成同一 bundle。 |
| `chatgpt_result` | no | 仅阶段 2 resume：外部 result ZIP 的绝对路径。必须与本轮按当前输入重新生成的 current bundle 的 handoff/source/job/hash 完全匹配；`wait` 下不完整结果绝不本地补算。 |
| `refresh_scope` | no | 仅阶段 3：`flagged`（缺省）/ `selected`（`套磁选择.json` 已选方向）/ `all`。 |
| `collection_key` | no | 仅阶段 3：精确限定一个方向（现役 runner 字段名保留，取值=该方向的 `direction_id` 兼容键）；传入后 plan/finalize 只处理该方向，不为其他方向生成模型 job。 |
| `kb_import` | no | 仅阶段 2：`true` 时把每篇相关论文的分析做成 KB 条目入库（tag 含 `zotero://…/<item_key>`，source=分析文件，重跑走 `updateKnowledge` 原地更新）；缺省 `false`。相关论文全量入库为后续项。 |
| `selection` | no | 仅阶段 4：直接传选择内容（见该 agent 说明），跳过交互提问。 |
| `mode` | no | 仅阶段 5：`first`、`both`、`followup`；generator 缺省按 `both` 调用，runner CLI 为兼容旧脚本缺省 `first`。 |
| `followup_template` | no | 仅阶段 5：跟进模板绝对路径；缺省查找 `套磁邮件/套磁跟进模板.md`。 |
| `skip_validation` | no | 仅阶段 5：true 时跳过 validator 循环（调试用）。 |

**Do NOT** load this skill's body into the subagent prompt — just pass the inputs; the subagent loads its own instructions.

## Persisted output — 教授研究/ folder

- `教授研究/套磁目标.json` — Stage 0 机器状态：每个被选教授的 target（稳定 `direction_id`、provisional `members[]`、`member_fingerprint`、representatives、user_note、preview 路径/指纹、`selection_history`）。**无 Stage 0 Markdown 产物**（旧 `套磁候选总览.md` 已退役）；禁止手改，经 `contact_targets.py` 维护。
- `教授研究/套磁阶段1候选.json` — Stage 1 机器状态（schema 1 / kind `professor-contact-stage1`）：逐被选教授/方向记录 provisional member keys、expanded candidate keys、逐篇 expansion reasons（+overlap `expansion_evidence`）、精确依赖指纹 `input_fingerprint`（v2：被选方向身份+provisional keys、被选方向词面画像字段、全部 preview 方向的 membership/confidence、`title`/`title_zh` 覆盖全部论文、`pdf_status` **仅对候选集**——仅覆盖能改变候选成员/就绪的输入；非候选论文 pdf_status 变化、整 preview 指纹变化但依赖不变时不再误触发重建）、PDF readiness 汇总与 `work_queue_item_keys`/`missing_item_keys`（工作队列=候选并集去重，只把缺失 keys 送 item 级 `pdf_only`）。`membership_claim` 恒为 `non_final_candidates_only`；禁止手改，经 `contact_stage1.py build` 维护；**无 Stage 1 Markdown 产物**。
- `<教授名>/套磁候选分析.md` — 阶段 2（v2 模板）：每方向四节——「方向定位」（可信度一句+署名线一句+分要点时间线，论文小总结只在此讲一遍）、「论文一览」（唯一表格：论文｜年份｜署名｜分析）、「与我的契合」（note 逐字+评估-only）、「可延伸方向」（【作者 future work】四件套=原文摘录/中译/大白话解释/gap_status；【我的延伸】带差异点；done_by_self 单列「已被本人实现」小节）。人读文本零 item key：首现全称+zotero+[分析] 链接，此后《固定缩写》（年份）挂同一链接。重跑=全量重写，无「本轮新增」式追加。
- `<教授名>/论文分析/_index.json` + `<作者>/<标题>.md` + `<作者>/<标题>.md.future_work.json` + `<作者>/<标题>.md.facts.json` — 阶段 2：完整分析的 future-work sidecar 优先（本地 PDF full 另产 `.facts.json` 结构化事实 sidecar：`paper` 元数据、research_problem/object/approach、findings/contributions/topic_terms/limitations、`input_fingerprint` 源 PDF 指纹与精确 join 的 `future_work_ids`）；旧分析只迁移当前相关论文，仍缺才只跑该篇 `gap-only`。`_index.json` 由阶段 2 独占写入，根为 `schema: 2`、`future_work_schema: 1`；每篇 `gaps[]` 只存 `gap_id`、`status`、`evidence`，原文/翻译/出处只在 sidecar，另记 `facts_sidecar`/`facts_state`/`facts_error`（valid｜unavailable｜failed + 稳定 reason）。旧 `gap`/`gap_zh`/`gap_source`/`gap_status` 字段暂保留兼容。
- `<教授名>/论文分析/_ocr/<标题>.txt` — 阶段 2：扫描版 PDF 的 LLM OCR 产物（含元数据头 + 逐页文本 + 图描述；复用 vision-tools glance 链；不入库、无 `llm_ocr` 标记；重跑复用）。
- `<教授名>/论文分析/_chatgpt_handoff/stage2-<handoff_id>/` + `.zip` — Stage 2 portable execution handoff；只含 post-cost-gate/post-idempotency 待分析 jobs、最小方向上下文与确定性 future-work 候选。`_latest.json` 只做 stale guard；这些文件是瞬时执行输入，**不是后续阶段事实源**。
- `<教授名>/套磁候选输入.json` — 阶段 2：按方向组织的最小事实包（支撑论文——fulltext 论文带 runner 校验过的规范化 `paper_facts`（来自 `.facts.json` sidecar，含 `facts_state`，指纹不符即 fail closed）、gap shortlist 全证据、排除清单+原因、`completed_gap_blacklist`、版本关系、红线、user_note、narrative、`input_fingerprint`）。阶段 3 **唯一**事实源；不含 profile。
- `<教授名>/论文分析/_freshness_cache.json` — 阶段 2：逐 gap freshness 缓存（status/model_evidence/candidate_paper_ids/gap_fingerprint/candidate_fingerprint/evaluated_at/confidence/completed_part/remaining_gap；无 TTL，指纹任一变化只失效受影响 gap）。
- `<教授名>/套磁候选状态.json` — 阶段 3：规范化候选状态（candidate_meta 的 gap_ids 在此，不在 Markdown）；profile/输入包指纹在此。
- `教授研究/邮件输入.json` — 阶段 4：程序级邮件输入包（精确 join 的 gap 短证据、真实标题、红线+banned_phrases、allowed_sources、source_hash），自包含——阶段 5 与 validator 只读它，不读上游。
- `<教授名>/套磁邮件状态.json` — 阶段 5：逐 email 保存首封的 model_result/choices/render sha/validation，以及 `followup` 子对象的文件、render sha/validation。validator 结束后由 runner `stage5-record-validation --professor-dir <教授目录> --validation-file <validation.json>` 原子写入实际 `pass|fail_after_2_rounds|skipped` 结果。
- `<教授名>/套磁想法候选.md` — 阶段 3（v2 模板）：方向节开头指路分析文件+共享红线一次 → 「你的草稿修正版」（保真/校准/基本方向）→ 每候选七件套（一句话大白话·强制启发链三段式「我的兴趣起手 → 教授的具体工作或原话 → 启发我探索的方向」，pivot 不得落在教授局限上（不足式表述只进「张力点」） / 研究问题行·求知式表述 / 要点式展开挂缺口编号+≤30 字摘录 / 五列支撑论文表：论文｜年份｜署名｜作用｜分析 / 贴合度 / 仅本候选红线 / 为何值得推吸收原匹配评估材料）→ 推荐优先级 2-3 行文字（兴趣契合作主推依据，能力匹配仅说明；纯交付物候选降为「配套承诺：」并入主候选）；写盘后过 `professor-contact-style-validator` 白话校验。原阶段 2 的想法级匹配评估材料整体搬到这里。
- `教授研究/套磁想法候选总览.md` — 阶段 3 聚合（跨教授，供异步挑选）。
- `教授研究/套磁选择.json` — 阶段 4：用户挑选结果（每方向选中的想法 + 支撑论文 item_keys），供阶段 5 消费。
- `<教授名>/套磁邮件.md` / `.txt` — 阶段 5首封邮件；无回复版本为同目录的 `套磁跟进邮件.md` / `.txt`。两类文件均有独立的送信前核对表、humanizer 保护校验和 validator 记录；跟进文件额外记录首封 email_id 与初次发送日期。
- `<教授名>/_contact_verify.json` — 阶段 5：教授级核验缓存（各项目 verdict＋来源＋时间戳＋info.json/boshu_analysis.json 指纹）；指纹变化或 >30 天才重核。同一教授多封邮件共享。
- `教授研究/套磁邮件总览.md` — 阶段 5 聚合（教授/方向/**收件邮箱｜核验状态**/首封链接/跟进链接）。

## 论文引用链接约定（本地 md 引用论文分析文件）

所有落到 `<教授名>/` 下的本地 md（套磁候选分析.md、套磁想法候选.md、教授研究导读.md、研究方向.md 等）引用论文时：

- **有分析文件 → 引用升级**：`（[zotero](zotero://select/library/items/<KEY>)）` 后追加 `｜[分析](<相对路径>)`，链接文案固定「分析」，相对路径以**引用文档所在目录**为基准。判定「有分析文件」= `<教授名>/论文分析/_index.json` 的 `papers[key].file` 非空；路径一律从 index `file` 原文派生（子目录名可能有空格差异，不得手写）。
- **没有分析文件 → 保持原样**：只留 zotero:// 链接。绝不凭空猜测分析文件路径。
- **不加 [分析] 的边界**：Zotero 内部 note（跨应用无锚点）、聊天回复、套磁邮件正文（模板+红线约束不放链接）、该教授没有 `论文分析/` 目录（事后可 `--backfill` 补）。
- 批量补链/校验/去重用 `skill(name: "paper-analysis-linker")` 的稳定命令 `paper-analysis-link`（`--backfill --dry-run` 预览 → 幂等真跑；`--map` 对账；`--dedup` 清重复分析文件）。Provider: `ScholarWorkflow/paper-analysis`; install with `uv tool install git+https://github.com/ScholarWorkflow/paper-analysis.git`; preflight with `command -v paper-analysis-link`。

## Behavior notes for callers

- **handoff barrier 是 Stage 2 的固定副作用**：每次有待分析 job 都先生成 ZIP；`continue` 随后按旧路径本地执行，`wait` 在任何新 OCR/逐论文模型调用前返回 `needs_external_result`。resume 先重建 current bundle 再验 result，防止旧 PDF/note/scope 结果被误装。
- **facts sidecar-first（fulltext 论文机器事实主源）**：本地 PDF full 三件套（`.md`/`.future_work.json`/`.facts.json`）在本地与 ChatGPT handoff 两条路径语义一致——handoff 的 PDF job 也必须带 facts 草稿并经本地 `facts.py finalize` 验证落盘。Stage 2 只复用通过校验（schema/generator/`analysis` 名/`evidence_level`/`input_fingerprint`==当前 PDF sha256/`future_work_ids` 精确 join 当前 future-work sidecar）的 facts，并以规范化 `paper_facts` 进入输入包；校验失败按 `facts_state=failed` fail closed。摘要级/OCR-only/legacy 论文 `facts_state=unavailable`，诚实保持证据等级；**任何路径都绝不为补 facts 触发第二次全文模型 pass**，`.future_work.json` 始终是引用证据的唯一权威。
- **每阶段独立跑、可中断**：PDF 下载（阶段 1，最慢）可单独丢后台；分析（2）/想法（3）可重复跑（改 profile 后重新生成想法不需要重下 PDF，也**不需要重跑阶段 2**——profile 已移出阶段 2；重跑阶段 2 靠输入包指纹 + `_index.json` 幂等——输入包指纹未变的方向直接复用，`_ocr/` 产物复用，freshness 缓存命中不重判）。阶段 2 只跑**相关论文**（默认 `relevant`，相关集 >10 篇会先问确认），扫描版论文会走逐页 OCR（较久）后再做 paper-analysis。旧产物迁移见「确定性 runner」节 `migrate-v3`。
- **Zotero 在线要求按阶段区分**：Stage 0 与 Stage 1 的候选构建全本地（读 `方向预筛.json`/`套磁目标.json`/`papers.json`，写 `套磁阶段1候选.json`），不需要 Zotero；阶段 1 的定向补下与阶段 2 的读元数据/摘要/附件才需要 Zotero 在线，离线时 agent 会提示打开 Zotero。
- **排序依赖**：Stage 0 只能在 professor-topic-clustering(`preview:true`) 产出 normalized `方向预筛.json` 之后跑；被选方向成员身份变化（成员 `item_key` 集合变化或方向消失）→ 阶段 1/2 以 `needs_refresh` 停止，须回 Stage 0 修订选择；未选方向、display 元数据或置信度变化不阻断。阶段 2 前置条件 = Stage 1 快照存在且 `contact_stage1.py verify` 通过（快照缺失/过期 → `needs_input` 重跑 Stage 1），分析范围取逐方向 `candidate_keys`。阶段 2 依赖阶段 1 候选集的 PDF 尽量全（有 PDF 的论文走全文深度分析；扫描版才触发 OCR；摘要缺失时仍可用 abstractNote 分析，PDF 只是增强）；候选集中暂时 `no_env`/`failed` 的论文按摘要参与分析，换网络后重跑 Stage 1 只补缺失候选。
- **诚实**：分析/想法严格基于论文实际内容与 profile；想法候选是「贴合论文方向的候选」，是否真实符合你想法由你在阶段 4 挑选决定（平衡原则）；阶段 5 邮件绝不编造 profile 之外的信息。
- **阶段 5 只产兴趣段**：详见「阶段 5 — 套磁邮件」专节（只产兴趣段 / 模板占位符 / Subject 构造 / 红线硬约束 / 志望默认非第一 / humanizer-ja 过稿 / 校验循环）。

## Retired behavior

以下行为已退出本 workflow 契约（磁盘上的历史文件可以保留，但任何阶段都不得把它们当 target state 消费）：

- Zotero 固定标题 `套磁候选` note 作为必需输入；
- `教授研究/套磁候选总览.md` 作为 Stage 0 输出；
- Stage 1/2 重新扫描 Zotero 来「发现」被选方向；
- 用 Zotero 方向 `collection_key` 充当套磁方向身份（`collection_key` 现在只是 `direction_id` 的兼容 join 键）。

## Synergy — pipeline
```
1. professor-collector (skip_pdf)            → Phase A 条目/元数据
2. professor-topic-clustering (preview)      → 方向预筛总览（用户定保留名单）
3. professor-collector (pdf_only, 保留名单)   → 保留教授下 PDF
4. professor-topic-clustering (增量, 保留名单) → 正式聚类 + preview:true 产出 normalized 方向预筛.json
   ── professor-contact Stage 0：交互选定方向（可写 per-direction user note）→ 写 教授研究/套磁目标.json ──
5. professor-contact (Stage 1-4)             → 逐方向候选快照+定向补 PDF / 分析 / 想法候选 / 选择记录
6. professor-contact-email-generator（阶段 5）→ 套磁邮件（兴趣段 + 模板拼装 + humanizer-ja 过稿 + validator，见「阶段 5 — 套磁邮件」节）
```
