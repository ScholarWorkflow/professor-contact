# Professor-contact 当前工作流参考

> 本文是 `professor-contact` 跨仓库开发时的**当前业务流程参考**。它描述机器事实源、阶段边界、跨仓库职责和允许的数据流，不替代各 agent / runner 的精确输入 schema。
>
> 当本文与实现冲突时，以当前 producer 仓库的 deterministic runner、schema 校验和 agent contract 为准；改变这些 contract 的 PR 应同步更新本文。
>
> 更新基线：2026-09-29。当前 `professor-contact` / `professor-research` 均支持 `opencode` 与 `codex` 两个 target；runtime 的委派方式不同，但本文中的业务状态机和事实源边界相同。

## 1. 当前总原则

1. **Stage 0 不再使用 Zotero 固定标题 `套磁候选` note。** 当前选择入口是 `professor-topic-clustering(preview:true)` 产出的 normalized `方向预筛.json`，机器方向身份是稳定 `direction_id`。
2. **正式 Zotero 聚类不是 professor-contact 前置条件。** `preview:false` 的正式聚类是可选的 Zotero 组织投影；outreach 的方向权威在 Stage 2 全文证据解析后形成。
3. **Stage 1 不再先给“保留教授”全量补 PDF。** 它先按被选方向构建保守高召回候选集，再仅把缺 PDF 的 `item_key` 交给 `professor-collector(pdf_only:true, item_keys=...)`。
4. **Stage 2 是学术证据与方向归属的权威层。** preview membership 只是 provisional；全文 facts / future-work sidecar 与 resolved-direction 状态决定后续 outreach 事实。
5. **Stage 3、Stage 4 与 Stage 5 都有唯一事实源。** Stage 3 只消费 `套磁候选输入.json`；Stage 4 的选择和邮件包按教授目录分别提交 schema 3；Stage 5 只消费该教授 Stage 4 成功结果交出的本地 `邮件输入.json`（`--email-pack`），再加 profile/template/info/boshu/verify 等允许的非论文输入。
6. **Markdown 是人类投影，不是反向输入。** 受管 Markdown 不得被后续阶段重新解析成机器状态。
7. **模型只做语义判断；确定性 runner 负责身份、join、fingerprint、缓存、校验、原子写与渲染。**

## 2. 端到端主流程

```mermaid
flowchart TD
    BO["程序目录 / boshu_output<br/>info.json + 招生材料"]
    C0["professor-collector<br/>skip_pdf"]
    PAPERS["教授研究/**/papers.json<br/>条目 / 元数据 / 摘要状态"]
    PRE["professor-topic-clustering<br/>preview:true"]
    PJ["方向预筛.json<br/>normalized provisional boundary"]

    S0["Stage 0 · professor-contact<br/>选择 direction_id + 可选 user_note"]
    TARGET["<教授目录>/套磁目标.json<br/>selected provisional target<br/>每位被选教授一份"]

    S1["Stage 1 · professor-contact-downloader<br/>resolve targets + build candidates"]
    CAND["<教授目录>/套磁阶段1候选.json<br/>membership_claim: non_final_candidates_only<br/>每位被选教授一份"]
    FILL["professor-collector<br/>pdf_only:true + item_keys<br/>仅缺失候选 PDF"]

    S2["Stage 2 · professor-contact-analyzer<br/>preflight + full evidence + direction resolution"]
    RD["论文分析/_resolved_directions.json<br/>authoritative full-text direction state"]
    INPUT["套磁候选输入.json<br/>Stage 3 唯一事实源"]

    S3["Stage 3 · idea-generator<br/>每 resolved direction 生成 / 修正 3–5 个想法"]
    STATE3["套磁候选状态.json<br/>canonical candidate state"]

    S4["Stage 4 · selection<br/>逐教授事务：用户选择 + fingerprint + exact join"]
    SEL["教授目录/套磁选择.json<br/>schema 3 · professor-local authority"]
    MAIL["教授目录/邮件输入.json<br/>Stage 4 交给 Stage 5 的 --email-pack"]

    S5["Stage 5 · email-generator<br/>一位教授 owner 调用 = 一个教授事务<br/>送信前核验 + 动态字段生成 + 确定性拼装"]
    VAL["professor-contact-email-validator"]
    OUT["套磁邮件 / 套磁跟进邮件<br/>.md + .txt + state"]
    OV["教授研究/套磁邮件总览.md<br/>派生投影：stage5-rebuild-overview"]

    FORMAL["professor-topic-clustering<br/>preview:false<br/>可选 Zotero 组织投影"]

    BO --> C0 --> PAPERS --> PRE --> PJ --> S0 --> TARGET --> S1 --> CAND
    S1 -->|"missing candidate item_keys"| FILL
    FILL -->|"完成后强制 rebuild Stage 1 snapshot"| CAND
    CAND --> S2 --> RD --> INPUT --> S3 --> STATE3 --> S4
    S4 --> SEL
    S4 --> MAIL --> S5 --> VAL --> OUT
    OUT -.->|"单独重建，finalize 不写"| OV
    PRE -.->|"独立可选，不是 contact 前置"| FORMAL
```

### 与旧流程相比已经退役的路径

- Zotero 固定标题 `套磁候选` note → Stage 0 target state；
- 程序级 `教授研究/套磁目标.json`（schema 1 / kind `professor-contact-targets`）作为 Stage 0 权威 → 现为纯迁移输入：只在建立某位教授的第一份 local target 时，由 `contact_targets.py bootstrap` 按该教授自己的目录读取一次并逐条 fan-out（standalone `migrate` 复用同一套 first-establishment helper），旧文件本身不删不改；
- `教授研究/套磁候选总览.md` 作为 Stage 0 机器/人类输出；
- 先按 professor keep-list 给教授全部论文补 PDF，再进入 contact；
- 用 Zotero direction `collection_key` 作为套磁方向机器身份；
- 正式 Zotero clustering 作为 professor-contact 的前置步骤；
- Stage 3/5 回读上游 Markdown、Zotero 或论文 PDF 重新构造事实。

历史文件可以保留，但不能重新进入当前状态机。

## 3. 各阶段职责与权威产物

| Stage | 主要执行者 | 当前输入边界 | 当前权威输出 | 下游约束 |
|---|---|---|---|---|
| 0 | `professor-contact` | normalized `方向预筛.json` | 逐教授 `<教授目录>/套磁目标.json`（每位被选教授一份） | 使用稳定 `direction_id`；一次 `select` 只提交一位教授；无 Stage 0 Markdown |
| 1 | `professor-contact-downloader` | 该教授的 local target + preview + `papers.json` | `<教授目录>/套磁阶段1候选.json` | 一次只 `resolve`/`build --target-file` 一位教授；只写该教授自己那份，不读不写其他教授的状态，也不读程序级聚合；仅候选集；归属声明必须是 non-final |
| 2 | `professor-contact-analyzer` + `paper-analysis` | 该教授的 local target + verified Stage 1 snapshot + 本地论文证据 | `_resolved_directions.json`、`套磁候选输入.json` | 全文 resolved direction 对 outreach 权威；input pack 是 Stage 3 唯一事实源 |
| 3 | `professor-contact-idea-generator` | `套磁候选输入.json` + profile | `套磁候选状态.json` + `套磁想法候选.md`（教授本地事务）；总览由 `stage3-rebuild-overview` 从全部已提交状态重建 | 不读 Markdown / `_index.json` / sidecar；默认每方向 3–5 条；教授本地提交不被其它教授/总览/registry 异常阻塞，总览不反向进入 Stage 4 事实源；首轮成功 plan 经 `--capture-invocation` 捕获该轮独占调用凭据（返回 `invocations` 列表），finalize/凭据修正消费凭据（`--invocation-file`/`--invocation-sha256`，与来源参数互斥）；`selected` 范围必须使用显式教授本地 `--selection`，不回退到程序级选择文件 |
| 4 | `professor-contact-selection` | `套磁候选状态.json` + 用户真实选择 | `<教授目录>/套磁选择.json`、`<教授目录>/邮件输入.json` | 以 canonical `professor_dir` 为事务边界逐教授提交，一次聚合 `results[]` 可 partial；exact `direction_id` / `(direction_id,item_key,gap_id)` join；该教授过期零写入，无关教授不阻断、不撤销已提交教授 |
| 5 | `professor-contact-email-generator` | 该教授的 `<教授目录>/邮件输入.json`（`--email-pack`）+ profile/template/info/boshu + verify cache | 邮件 md/txt、跟进邮件、`套磁邮件状态.json` | `邮件输入.json` 是论文事实与冻结联系方式的唯一事实源；一次 owner 调用 = 一个教授事务，程序级总览改由 `stage5-rebuild-overview` 单独派生 |

## 4. Stage 0：从 preview 选择目标方向

Stage 0 直接消费 `方向预筛.json` 的 normalized contract。至少依赖：

- `preview_fingerprint` / `preview_fingerprint_version`；
- `direction_id_version`；
- `membership_mode: overlap_allowed`；
- 每方向稳定 `direction_id`；
- 完整 `members[]`，每个 member 含 `item_key` 与 `preview_confidence`；
- `member_fingerprint`；
- 人读名字、summary、representatives。

用户可以多选方向，并为每个方向提供 `user_note`。A/B/C、方向显示名与 Zotero collection key 都不是机器身份。

Stage 0 的权威状态是**每位被选教授一份、只描述该教授自己**的 `<教授目录>/套磁目标.json`（schema 2 / kind `professor-contact-target`，无 `targets[]` 信封、无程序级索引文件）。路径由被校验的 preview 反推（`<preview 的父目录>/套磁目标.json`），调用方不传也不猜。建立与修订分工固定：`bootstrap` 是唯一建立该教授第一份 local v2 的入口，`select` 只修订已存在的 local（文件缺失返回 `bootstrap_required` 且零写入）。一位教授一笔事务、一次调用只写该教授那一份；多教授请求逐笔提交，已提交的教授绝不因后续教授失败而回滚或被重写，同名不同目录的两位教授各算一笔事务。Stage 0 → Stage 1/2 的交接是教授级事务记录数组（`transactions`，每条含 canonical `professor_dir`、`preview_path` 与实际 `target_state`），不是以教授展示名为 key 的映射。旧程序级 `教授研究/套磁目标.json` 只在 first-establishment 时按该教授目录读取一次，运行期 select/resolve/Stage 1/Stage 2 一律不再读它。

```mermaid
flowchart LR
    PRE["方向预筛.json"]
    UI["用户选择一个或多个方向<br/>可填写 per-direction user_note"]
    ID["stable direction_id"]
    T["<教授目录>/套磁目标.json<br/>每位被选教授一份"]

    PRE --> UI --> ID --> T
```

当被选方向的成员 `item_key` 集合变化或方向消失时，需要回到 Stage 0 重新确认；未选方向变化、纯 display 变化以及不改变成员身份的投影变化不能被当成整个 contact workflow 的无条件失效信号。

## 5. Stage 1：方向候选集与 item-scoped PDF fill

Stage 1 的候选集是**保守高召回输入范围**，不是最终方向归属。候选来源可以包括 provisional members、低置信成员、与被选方向有本地廉价证据重叠的他向/未安置论文，以及用户显式点名论文。

```mermaid
flowchart TD
    T["<教授目录>/套磁目标.json"]
    P["方向预筛.json + papers.json"]
    R["contact_targets.py resolve<br/>--target-file 一位教授"]
    B["contact_stage1.py build<br/>--target-file 同一份"]
    Q{"candidate PDF readiness"}
    N["noop"]
    F["professor-collector<br/>pdf_only:true + item_keys"]
    RB["post-fill contact_stage1.py build<br/>--target-file 同一份"]
    S["套磁阶段1候选.json"]

    T --> R
    P --> R --> B --> Q
    Q -->|"全部 usable"| N --> S
    Q -->|"有缺失 item_keys"| F --> RB --> S
```

关键边界：

- `item_keys` fast path 与 professor keep-list 是两种不同语义；contact Stage 1 只能使用 item-scoped fast path。
- `item_keys` 与 `professors` 不得同时用于 Stage 1 的定向补下。
- Stage 1 一次只处理一位教授：`resolve`/`build`/`verify` 都要求显式 `--target-file <教授目录>/套磁目标.json`，绝不回退读旧程序级表；快照内其他教授的条目由按教授 merge 保留。
- `access_mode` 只有在 caller 已取得真实用户决定时才显式传 `oa_only|allow_non_oa`；不得在生产 contract 中偷偷造默认值。
- collector 修改 `papers.json` 后必须重建 Stage 1 snapshot；Stage 2 只能消费 post-fill snapshot。

## 6. Stage 2：证据、handoff 与 authoritative direction resolution

Stage 2 是当前最重要的学术权威边界。它首先做 cheap preflight；缓存证明完整时可以在 Zotero/PDF/OCR/model 之前 `reuse_all`。未命中时才进入全文证据链。

```mermaid
flowchart TD
    C["该教授的 local target<br/>+ verified Stage 1 candidate snapshot"]
    PF["contact_state.py stage2-preflight<br/>--target-file <教授目录>/套磁目标.json"]
    DEC{"preflight result"}
    REUSE["reuse_all<br/>复用已有 input pack / projection"]
    U["selected directions 的 candidate union"]
    H["确定性 ChatGPT handoff bundle<br/>执行通道，不是事实源"]
    HM{"chatgpt_handoff"}
    LOCAL["continue：本地继续 OCR / paper-analysis"]
    WAIT["wait：在新 OCR / paper-analysis 前软停止"]
    IMPORT["匹配 result ZIP<br/>本地严格校验并安装规范产物"]
    PA["paper-analysis full<br/>按 item_key 去重与复用"]
    FW[".future_work.json<br/>作者明说 future work"]
    FACT[".facts.json<br/>normalized full-text facts"]
    RP["stage2-resolve-plan"]
    RM["resolution model job"]
    RF["stage2-resolve-finalize"]
    UC{"material change?"}
    ACCEPT["用户明确 accept / keep provisional"]
    RD["_resolved_directions.json<br/>accepted authoritative state"]
    P2["stage2-plan"]
    F2["stage2-finalize --preflight-file"]
    OUT["套磁候选输入.json<br/>+ freshness cache + Markdown projection"]

    C --> PF --> DEC
    DEC -->|"reuse_all"| REUSE --> OUT
    DEC -->|"process"| U --> H --> HM
    HM -->|"continue"| LOCAL --> PA
    HM -->|"wait"| WAIT
    WAIT -->|"提供匹配 result ZIP"| IMPORT --> RP
    PA --> FW --> RP
    PA --> FACT --> RP
    RP --> RM --> RF --> UC
    UC -->|"无 material change"| RD
    UC -->|"有"| ACCEPT --> RD
    RD --> P2 --> F2 --> OUT
```

### Stage 2 的事实优先级

- `.future_work.json`：作者明确 future-work 引用证据的权威 sidecar；不能把一般 limitation 推断成作者明说 future work。
- `.facts.json`：全文论文事实的规范化机器 sidecar；其 input fingerprint / future-work join 必须有效。
- `_resolved_directions.json`：preview provisional membership 经全文证据修正后的 outreach 方向权威状态。
- `套磁候选输入.json`：Stage 2 对下游暴露的最小规范事实包；Stage 3 不得绕过它回读上述内部文件。

ChatGPT handoff 只是“谁执行高成本逐论文分析”的可选传输层。外部 ZIP 不能直接提供权威 `_index.json`、future-work sidecar、facts sidecar、gap ID、resolved state 或 `套磁候选输入.json`；这些都必须经过本地 deterministic validator / finalize。

## 7. Stage 3：按 resolved direction 生成候选想法

```mermaid
flowchart LR
    I["套磁候选输入.json"]
    PROFILE["用户 profile"]
    PLAN["stage3-plan<br/>按 direction_id 切最小 model_input"]
    MODEL["每方向 3–5 条候选"]
    FIN["stage3-finalize<br/>教授本地事务<br/>MD 先装 / 状态最后装"]
    ST["套磁候选状态.json<br/>教授级正式状态＝提交标记"]
    MD["套磁想法候选.md<br/>教授本地投影"]
    REB["stage3-rebuild-overview<br/>terminal 后一次 best-effort"]
    OV["套磁想法候选总览.md<br/>程序级派生投影"]

    I --> PLAN
    PROFILE --> PLAN --> MODEL --> FIN --> ST
    FIN -.-> MD
    ST --> REB -.-> OV
```

约束：

- 默认逐 resolved `direction_id` 独立生成；显示名和 `collection_key` 不决定身份。
- `gap_refs` 必须精确到 `(direction_id, item_key, gap_id)`。
- cross-direction 候选是显式 opt-in；未传 `cross_direction_groups` 时不得偷偷生成跨方向 job 或 section。
- profile 变化影响 Stage 3/4，而不要求重跑 Stage 2 学术事实。
- **教授本地提交独立（issue #66）**：`stage3-finalize` 只读取/提交当前教授——候选状态与本地 Markdown 以一个本地事务写盘（Markdown 先安装、候选状态最后安装＝唯一提交标记；提交前普通失败恢复旧内容，提交后清理失败不回滚），绝不读写其它教授的状态、`套磁想法候选总览.md` 或 `_contact_projections.json`。其它教授状态异常、总览缺失/过期/被手改都不会阻塞、回滚或重判一次合法的教授本地提交。
- **总览只是派生投影**：`stage3-rebuild-overview` 在 terminal 校验后由 terminal owner（OpenCode=idea-generator；Codex=root caller）best-effort 运行一次，从全部已提交教授级 `套磁候选状态.json` 派生 `套磁想法候选总览.md`（教授/方向/候选数/推荐顺序/链接全部来自状态；本地 Markdown 只贡献链接路径；排序以 resolved professor 目录身份为跨教授 tie-breaker，方向/组按机器身份稳定排序）。任一已发现状态 malformed 或 legacy 身份无法精确迁移（0 个或多个 canonical `direction_id` 匹配）时，写总览之前整体失败，绝不发布部分总览；手工改动总览（frontmatter 无效或 body hash 失配）→ rebuild fail closed。aggregate 失败不修改教授本地状态，也不把 Stage 3 改回未完成；`overview_md` 只是目标路径，不是 rebuild 成功证据。
- **generator source-binding（issue-66-plan-r11 §4）**：每个 generator child 只解析一次 Stage 3 输入并形成固定 source tuple（`professor_dir`/`program_root`/resolved profile 路径/`refresh_scope`/skip/cross/修正轮 `validation_file`）；同一轮的 `stage3-plan` 与 `stage3-finalize` 必须用同一 tuple，存在 profile 时都显式传同一 `--profile <abs>`；plan 返回的 `profile_fingerprint` 为空或与该 profile 不一致 → child 当场返回 error，不写 result、不 finalize；runner 任一非成功返回（含 `validation_source_changed`）立即结束，不得换 source 重试。runner 的 `validation_source_changed` fail-closed 行为原样保留，无静默补救。
- **调用凭据与凭据修正（r13 §5）**：首轮 `stage3-plan --capture-invocation <本轮独占临时目录>` 在成功计划后由 runner 从实际解析参数生成该轮独占调用凭据，返回 `invocation_file`+`invocation_sha256`（凭据生产失败 = 计划非成功）；`stage3-finalize` 与凭据修正轮用 `--invocation-file/--invocation-sha256` 消费同一凭据，与重传 professor/profile/root/scope/skip/cross/direction/selection 来源参数互斥（混传即拒绝）；带已记录 `validation_file` 的凭据计划/提交进入 runner 的修正上下文——修正工作集合只由已记录校验问题计算（方向集合 `D`、组集合 `G`），首轮的方向/刷新/跳过/组请求不再裁剪修正范围，修正提交在旧方向/旧组集合内替换、集合外对象与未涉及组原样保留（r13 §5.4–§5.6，旧显式修正入口同样获得未涉及组保留）。生成代理最终返回增加按教授目录排序的 `invocations` 列表（每项 `professor_dir`/`invocation_file`/`invocation_sha256`），caller 按候选稿/状态文件的规范父目录绑定本次教授，不以展示名建映射。
- **校验原文文件交接（r16）**：每轮由循环持有者先运行 `stage3-prepare-validation --invocation-file/--invocation-sha256 --round {1,2}`，把返回的候选稿绝对路径、`artifact="candidates"` 和指定 `output_file` 交给命名校验子线程（不给状态、凭据、交接元数据或其他文件）。带 `output_file` 时，校验者只产出一份完整业务 JSON 对象（`result`、`files[]`、`notes`），将完整 JSON 作为一个独立且安全引用的 `--result-json` 参数交给固定入口 `.agents/skills/professor-contact/scripts/contact_state.py stage3-write-validation`，不得自行写文件。单候选使用 `--output-file <已准备的绝对输出路径>`；批量使用 `--output-map-json <完整映射 JSON>`，其中 `file` 与 `output_file` 必须逐一对应本轮全部候选稿，不得重复、遗漏、增加候选稿或复用输出路径。完整 JSON、映射和路径都须分别作为单一、安全引用的参数传入，不得让 shell 解释其内容。固定入口拒绝重复 JSON 键、非有限数字、无效结构、已存在的路径或符号链接；它先校验全部输入，只将完整结果序列化一次，再以排他创建、权限 `0600` 写入同一份完整结果，并从同一文件描述符回读核对。固定 writer 的成功 stdout 与各输出文件逐字节相同，这是 writer 的写入约定。**Codex 带 `output_file` 时，validator 最终消息只返回固定完成报告**：成功为 `{"result":"ok","write_status":"written","output_files":["<指定输出文件绝对路径>"]}`；失败为 `{"result":"error","write_status":"failed","output_files":["<本轮指定输出文件绝对路径>"],"reason_code":"<入口原因码；缺少时为 validation_write_failed>"}`，不得包含校验结论、问题或校验正文。`output_files` 必须覆盖所有指定输出路径，批量时按候选稿顺序排列。root 只核对固定报告的结构、状态、输出路径及失败原因码；成功后只用 `stage3-prepare-validation` 返回的 `handoff_file`/`handoff_sha256` 运行 save，再用 save 返回的 `validation_sha256` 运行 record。报告本身不作为校验结果，root 不从中提取或重建校验正文；报告缺失、结构或路径不符、或报告为失败时立即停止，不运行 save/record，固定写入文件是唯一正式校验原文。**OpenCode 保留现有行为**：validator 最终消息仍须与固定 writer 输出及指定文件逐字节相同。save 与 record 严格依次运行，由 runner 搬运并记录同一份原文字节；caller 不重构字段、翻译或重新定权。未传 `output_file` 的既有校验调用保持只读并沿用原返回方式。
- **Codex caller 固定状态转移（r16 §7；root 的合法路径只有以下两条）**：路径为 `G1 成功 → prepare(1) → V1 固定 writer 写入成功且完成报告有效 → save(1) → record(1) → terminal → rebuild once → end`，或在 `record(1)` 返回 `needs_correction=true` 后进入 `G2 → prepare(2) → V2 固定 writer 写入成功且完成报告有效 → save(2) → record(2) → terminal → rebuild once → end`。G1/G2 或固定完成报告任一非成功，都在下一依赖动作前立即停止；不派发第三次 validator 或任何 retry generator。成功路径 root 直属 Stage-3 child 总数只能是 2 或 4，第 5 个即 caller contract violation；中途失败只能是合法路径的前缀，不算完成。Codex=root caller 在自己线程执行 prepare/save/record 并按上述循环派发命名子线程；OpenCode=生成代理持有校验循环，由它在自己线程按既有交接规则执行 prepare/save/record，不照搬 Codex 根与兄弟子线程结构；两个 runtime 都最多两轮校验。

## 8. Stage 4：真实用户选择与邮件包编译

Stage 4 的选择源是 `套磁候选状态.json`，不是 Markdown。没有真实用户选择就不能 finalize。一次调用按 canonical `professor_dir` 分组，每位教授是一个独立事务：一位教授的 expected 失败既不阻断也不撤销另一位已提交的教授，runner 只输出一个聚合 JSON（`status=ok|partial|error` + `results[]`）。

caller 逐行消费 `results[]`：`partial` 只把 `status=ok` 行的 `email_pack` 原路径交给阶段 5（`--email-pack`），失败行按自己的 `reason_code` 单独修复。runner 因编程异常中断时没有聚合 JSON，因此也没有任何成功行可 handoff——重新委派正式 Stage 4 owner `professor-contact-selection` 重新处理这批显式选择，从各教授已有的 local 权威与当前阶段 3 事实进入，已提交的教授不被回滚或删除。

```mermaid
flowchart TD
    ST["套磁候选状态.json<br/>该教授"]
    USER["用户真实选择"]
    F["stage4-finalize<br/>逐教授事务"]
    G{"fingerprint + scope + exact gap join"}
    STOP["该教授 needs_refresh / error<br/>该教授零写入"]
    SEL["教授目录/套磁选择.json<br/>schema 3"]
    MAIL["教授目录/邮件输入.json<br/>schema 3"]
    AGG["聚合 results[]<br/>ok / partial / error"]

    ST --> F
    USER --> F --> G
    G -->|"失败"| STOP
    G -->|"通过"| SEL
    G -->|"通过"| MAIL
    SEL --> AGG
    MAIL --> AGG
    STOP --> AGG
```

该教授的 `<教授目录>/邮件输入.json` 编译并冻结；Stage 4 成功结果中的 `email_pack` 是 Stage 5 后续调用传入 `--email-pack` 的唯一来源：

- 选中 idea 与 `direction_ids`；
- 方向 display provenance；
- 按 `item_key` 去重的论文短证据；
- 每条 gap 的精确 `direction_id` / `item_key` / `gap_id`；
- red lines / allowed sources / source hash；
- 上游 `_联系方式证据.json` 中该教授的 contact evidence snapshot 与 record fingerprint。

从这一刻起，Stage 5 不再重构论文事实。

历史遗留的程序级选择行按教授逐个迁移：`stage4-migrate-local --program-root <程序根> --professor-dir <教授目录>` 只把该教授的 legacy 选择行当作行来源，邮件事实一律按当前 `套磁候选状态.json` + 输入包重编译（不复制 legacy 邮件行），完整 local pair 已存在即 `already_local` 原样保留，只有一半即 `local_pair_incomplete` 零写入，无对应 legacy 行即 `not_applicable`；legacy 程序级文件的字节始终不被修改，也不再被当作权威。

## 9. Stage 5：唯一邮件事实源、冻结联系方式与确定性拼装

当前第五阶段依据[第十七版完整计划](../../../../plan/issue68-implementation-plan.md)（`issue-68-plan-r17-2026-10-11`）；以下文件输入、单教授交接、委派顺序及清理规则覆盖旧调用说明。历史 `stage5-legacy-contract.md` 不作为当前接口来源。

```mermaid
flowchart TD
    MAIL["<教授目录>/邮件输入.json<br/>论文事实 + frozen contact_evidence<br/>--email-pack"]
    EXTRA["profile + template + info.json<br/>boshu_analysis.json + _contact_verify.json"]
    PLAN["stage5-plan"]
    SCOPE["--email-id 身份解析<br/>命中 0 → invalid_params<br/>命中 >1 → invalid_email_pack"]
    CE["contact-evidence freshness / fingerprint gate"]
    REFRESH["needs_refresh<br/>回 Stage 4 重冻结"]
    VERIFY["送信前核验"]
    MODEL["模型动态字段<br/>4 句兴趣段 + future aspiration + learning candidates + source_map"]
    HUM["humanizer-ja business<br/>仅动态字段，拼装前"]
    CHOICE["用户 choices"]
    ASM["stage5_immutable.py stage5-finalize<br/>确定性模板拼装 / 保护串 / 渲染"]
    VAL["email-validator<br/>只读最终 md + 邮件包"]
    OUT["首封 + follow-up<br/>md / txt / state"]
    OV["教授研究/套磁邮件总览.md<br/>stage5-rebuild-overview 单独重建<br/>finalize 从不写"]

    MAIL --> PLAN
    EXTRA --> PLAN
    MAIL -->|"派生投影"| OV
    PLAN --> SCOPE
    SCOPE --> CE
    CE -->|"snapshot 缺失或 live record 改变"| REFRESH
    CE -->|"一致"| VERIFY --> MODEL --> HUM --> CHOICE --> ASM --> VAL --> OUT
```

联系方式的关键语义：

- 邮件真正采用的收件地址来自 `邮件输入.json` 内冻结的 `contact_evidence`；
- live `_联系方式证据.json` / rebuild 只用于确认 source-state freshness 与 fingerprint；
- live/rebuild record 发生变化时，Stage 5 **不能直接采用新地址**，必须 `needs_refresh` 回 Stage 4 重编译邮件包；
- `_contact_verify.json` 才是送信核验 cache，但不能替代邮件包的冻结事实边界。

humanizer 的当前边界：只润色模型动态字段，且发生在模板拼装前。Subject、模板固定文字、用户选择短语、整封首封/跟进成品都不能交给 humanizer 重写。

单封定向范围（Issue #59）：`stage5-plan` 与 `stage5_immutable.py stage5-finalize` 都必须带该教授的 `--email-pack`，并且都可以带 `--email-id <id>`；同一次定向运行的每次调用必须传**同一个 `email_id`** 与同一个 pack 路径。runner 先按 `email_id` 解析出本次唯一范围，再依次做 pack 的单一教授归属、`professor_dir` 程序根约束、contact-evidence 新鲜度/指纹、`_contact_verify.json`、`套磁邮件状态.json`、result、choices、模板与写盘校验。因此无关条目的损坏或非 dict 形状既不会阻断这一封，也不会被读取或被写入；被选条目自身仍走全部既有 fail-closed 检查（含收件人权威）。找不到该 id → `invalid_params`（`email_id not found: <id>`）；同一 id 在包内出现多次 → `invalid_email_pack`，绝不按数组位置或教授名猜。

定向 finalize 是这一封邮件的事务：只写被选邮件的 md/txt 与 `套磁邮件状态.json`，不重建程序级 `套磁邮件总览.md`、不做聚合的投影冲突检测；总览已存在则结果 `overview_md` 给出其路径，不存在则为 `null`。校验侧同样按范围收敛：`professor-contact-email-validator` 只跑本次渲染出的那对 md，validation 文件只写被选输出的 id，`stage5-record-validation` 沿用 `--professor-dir` + `--validation-file`（它只记录调用方给出的那些行，因此不新增 `--email-id`）。

逐教授事务归属（Issue #68）：阶段 5 只承认 `--email-pack` 指向的那一份教授本地 `邮件输入.json`，程序级旧包不再是任何阶段 5 读取的兜底（缺失即 `invalid_params`/`needs_refresh`，无法证明单一教授归属即 `invalid_email_pack`；迁移归 Issue #67）。A、B 两位教授 = 两次 exact named `professor-contact-email-generator` owner 调用，每次业务处理只消费该教授的阶段 5 输入；B 的包/状态/核验损坏既不阻断 A，也不被 A 读写，B 失败不回滚 A 已提交的渲染；owner 调用之间的顺序与是否并行属调用方编排，不构成产品契约。批量模式（不带 `--email-id`）同样只覆盖 `--email-pack` 那一位教授，包内全部邮件一起验证并提交。阶段 5 有两条入口：紧接阶段 4 时，root 直接消费成功结果交付的确切 `email_pack` 路径；独立阶段 5 用只读命令 `contact_state.py stage5-list-inputs --program-root <abs>` 逐个发现教授本地包，逐行返回 `professor`、`professor_dir`、`email_pack`、`status`、`reason_code`——单个坏包只形成自己的失败行，不阻止其它有效教授，不读核验、状态、渲染、总览或程序级旧包，不写任何文件；发现只负责找包，不生成任何跨教授归属数据；`--professor` 只做唯一精确匹配，缺失或同名歧义返回 `needs_input`（`professor_not_found` / `professor_ambiguous`），不任选。`教授研究/套磁邮件总览.md` 改成派生投影：由 `contact_state.py stage5-rebuild-overview --program-root <abs>` 枚举各教授本地包、精确 join 其本地 `套磁邮件状态.json`、读取 `_contact_verify.json` 仅作展示后重建；任何教授的 finalize 都不创建、也不更新这份聚合，聚合陈旧、冲突或缺失都不阻断该教授提交。rebuild 不改动任何本地包/状态/邮件/核验文件，本地输入或状态畸形即 fail closed 且不覆盖既有聚合，聚合被人手改动只让 rebuild 返回 `needs_decision`。

选择归属与文件交接（第十三版计划第 3.3—3.5 节）：正式选择身份是 `(professor_dir, email_id)`，其中目录是规范教授身份，展示字段 `professor` 只用于显示。业务对象中的 `choices` 是结构化对象或对象列表；三个第五阶段命令的 `--choices` 都是 JSON 文件路径，不接受内嵌选择文本，也不根据字符串外观猜输入类型。

用户提供选择时，根代理用 JSON 序列化工具将原始值写入本请求独占的原始选择文件，不补字段、不翻译、不手工按教授切片。选定第四阶段实际交付或只读发现的本地包后，以参数列表启动 `contact_state.py stage5-partition-choices --program-root <实际项目绝对路径> --owner <email_pack> [email_id]… --choices <原始选择JSON文件绝对路径> --out <完整分配JSON文件绝对路径>`，每个规范教授目录恰好对应一个 `--owner`，保留其可选目标 `email_id`。原始选择文件只供根代理分配入口读取；`--out` 保存包含顶层字段和全部 `owners` 的完整对象，只供根代理解析，不能整份作为教授交接文件。

根代理读取实际退出状态及结构化返回；顶层错误、文件读取失败或没有合法分配结果时保留真实原因，不宣称已委派或完成业务。用 JSON 解析器读取 `owners`，按每项 `professor_dir` 对照本次选中包，不按展示名、返回位置猜归属；无法唯一对应时停止受影响交接并报告输入不一致。逐项检查 `partition.status`，非 `ok` 项保留实际状态、原因及相关字段，只停止该教授；顶层 `status: ok` 不代表全部教授可执行。合法项的实际 `choices_rows` 列表直接赋给该教授业务对象的 `choices`，即使只有一行也保留列表，不再次分配、排序、去重或删除错误行。

根代理程序化写入各自独占的 `owner_input_file`，只含对应教授的 `email_pack`、可选同一 `email_id`、本教授选择、实际 `program_root` 及已提供的普通参数；已提供的模型结果只能属于该教授，未提供参数沿用现有缺省规则。原始选择路径、完整分配文件、整个 `owners`、其他教授项及跨教授范围均不得交接。业务对象的目录、编号及选择值从解析字段取得，不能手工转抄到委派消息或命令字符串；子任务消息只含对应 `owner_input_file` 的绝对路径与本教授业务约束，不含等待、路由或 caller 指令。最后一个合法交接文件写完后，下一动作按当前安装目标专属说明进行原生委派。用户没有提供 `choices` 时，省略该字段，不造空值、不调用分配，仍按真实本地包形成单教授交接并正式委派，由业务代理按已有分支取得用户决定或返回 `needs_input`。

教授代理只解析自己的 `owner_input_file`，不读根代理原始选择、完整分配或其他教授数据。第一次 `stage5-plan` 保持同一包与可选目标，不带模型结果和选择，先处理业务核验；允许消费选择时才将本教授已解码的 `choices` 值原样序列化为自己独占的选择文件。后续以参数列表调用 `contact_state.py stage5-plan --email-pack <同一本教授邮件包路径> [--email-id <同一目标编号>] --choices <本教授选择JSON文件绝对路径>`，不可变模板提交使用 `stage5_immutable.py stage5-finalize --email-pack <同一本教授邮件包路径> [--email-id <同一目标编号>] --choices <同一本教授选择JSON文件绝对路径>`；其他已确定参数继续按现有命令要求传入。重规划和最终提交保留同一教授包、同一目标及同一选择，不重新归属；已有交互补齐时只使用实际用户决定。教授选择文件只由该教授业务入口读取，收件人、日期、缺失、重复及字段检查不变，同教授整批全部合法才提交。业务代理返回一条完整结构化结果，保留实际 `professor_dir/status/reason_code` 及相关信息，不把未核验、缺输入、失败或部分结果改称成功。

现有分配规则保持不变：显式带 `professor_dir` 的行只进入其指向的教授，不属于本次选中集合的行不进入任何交接；指定目标时先排除该教授未选中的编号，目标本身仍接受全部严格检查；整教授批量中的错误编号只让所属教授返回 `needs_input / choice_owner_invalid`。无目录旧行只按选中包的实际执行范围计算候选：无候选为无关行，一个候选进入该教授并参与重复检查；多个候选才排除已被合法显式行满足的教授，剩一个绑定，剩多个分别返回 `needs_input / choice_owner_ambiguous`，剩零个不改变已明确教授的结果，歧义行不广播。某教授分配失败不阻止其他合法交接被委派。若调用方错误夹入其他教授显式行，教授业务程序只以 `invalid_params` 拒绝当前教授并保持零部分提交，不向其他教授重新路由，也不当作无目录旧行重绑定。

临时文件归属与清理（第十三版计划第 3.6 节）：根代理拥有原始选择、完整分配及单教授交接文件；教授代理拥有自己生成的选择与结果传递文件。每次请求使用独占目录和程序生成的不含教授名称的文件名，不覆盖其他请求；这些文件只传递本次数据，不是长期事实来源。写入失败保留实际错误，不复用旧文件、不改用内嵌文本重试；原始选择不可读、非法 JSON 或顶层不是对象或对象列表时保留 `invalid_result_json`，不制造分配或逐教授成功。教授包、选择归属或交接失败只影响所属教授，共用原始选择无法可靠读取时先报告该输入问题。

消费者仍需读取时不得删除传递文件；根代理消费全部已委派结果并交付本轮结果后，各负责者清理自己拥有的本请求文件。正常结束、失败和取消采用同一归属；仍有读取者运行时，先按现有执行器结束处理再清理。仅清理可确认属于本请求的文件，不搜索删除其他目录；清理错误单独报告，不回滚或降级已形成的教授业务结果。

顶层顺序（第十七版计划第 3.5—3.7 节）：用户提供选择时根代理先完成一次确定性分配，缺选择时按上述省略字段的分支交接；所有合法交接文件写完后，按当前安装目标的原生路由逐教授委派、等待并消费已启动子任务的最终结果，同时保留分配阶段失败项。结果按规范 `professor_dir` 分别关联。若存在合法教授但没有任何对应子任务实际启动，说明尚未进入教授处理，停止正常总览与完成报告并清理本次文件；不得重建零人零封的正常总览。若只启动了部分教授，则等待全部已启动者，再按实际本地状态最多调用一次 `stage5-rebuild-overview`，单教授请求采用相同顺序。总览的 `ok / needs_decision / error` 结果单独报告，不改变、不回滚、不重跑、不降级任何教授结果；邮件生成代理不扫描其他教授目录。

校验侧不变：验证仍在该教授自己的事务内完成，`stage5-record-validation` 沿用 `--professor-dir` + `--validation-file`，不因 Issue #68 新增 `--email-id`。

## 10. 机器事实源与人类投影

```mermaid
flowchart LR
    P["方向预筛.json<br/>provisional"]
    T["<教授目录>/套磁目标.json<br/>每位被选教授一份"]
    C["套磁阶段1候选.json<br/>non-final candidates"]
    E["Stage 2 sidecars / facts"]
    R["_resolved_directions.json<br/>authoritative outreach direction"]
    I["套磁候选输入.json<br/>Stage 3 sole source"]
    S["套磁候选状态.json"]
    SEL["套磁选择.json"]
    M["<教授目录>/邮件输入.json<br/>Stage 5 sole source (--email-pack)"]
    ES["套磁邮件状态.json"]

    MD2["套磁候选分析.md"]
    MD3["套磁想法候选.md / 总览"]
    MD5["套磁邮件.md / 跟进邮件.md / 总览"]

    P --> T --> C --> E --> R --> I --> S --> SEL --> M --> ES
    I -.->|"render"| MD2
    S -.->|"render"| MD3
    ES -.->|"render"| MD5
```

**禁止反向箭头。** Markdown 的人手修改不能被解析回机器事实；受管投影冲突应返回 `needs_decision`，需要保留的用户内容必须通过正式机器入口写回状态。

## 11. 跨仓库职责

```mermaid
flowchart LR
    CONTACT["professor-contact<br/>Stage 0–5 orchestration + state runners"]
    RESEARCH["professor-research<br/>collector / preview clustering / contact evidence"]
    PA["paper-analysis<br/>论文分析 + future-work evidence"]
    PDF["pdf-processing-core<br/>PDF extraction / quality / OCR support"]
    Z["zotero-tools<br/>Zotero read/write/export helpers"]
    BP["browser-pdf-tools<br/>PDF acquisition adapter"]
    KB["knowledge-tools<br/>optional KB import"]
    BASE["base-skills<br/>shared runtime skills"]

    CONTACT --> RESEARCH
    CONTACT --> PA
    CONTACT --> PDF
    CONTACT --> Z
    CONTACT --> KB
    CONTACT --> BASE
    RESEARCH --> Z
    RESEARCH --> BP
    RESEARCH --> BASE
    PA --> PDF
```

这张图表达 producer 责任边界，不代表每一次 Stage 都会调用所有依赖。比如 Stage 3/4 不应该因为 manifest 存在 Zotero 依赖就重新读取 Zotero。

## 12. 双 runtime 边界

`professor-contact` 与 `professor-research` 当前 manifest 都是 `targets: [opencode, codex]`。业务状态机只有一份，但委派与用户输入边界按 runtime 适配：

- OpenCode 继续保留原生 Task / `question` / permission / depth 语义；
- Codex 使用安装后的 exact named custom agents，non-interactive 用户选择通过业务级 `needs_input` → 下一轮 fresh root invocation + 显式选择完成；
- 不把某一 runtime 的私有函数签名写成跨 runtime 产品 contract；
- 不允许为 Codex 适配而破坏既有 OpenCode production contract。

```mermaid
flowchart TD
    CONTRACT["同一份业务 contract<br/>Stage 0–5 + JSON state"]
    OC["OpenCode runtime adapter"]
    CX["Codex runtime adapter"]
    AG["exact named agents / skills"]
    STATE["同一套持久化机器状态"]

    CONTRACT --> OC --> AG --> STATE
    CONTRACT --> CX --> AG --> STATE
```

## 13. 修改工作流时的开发检查表

变更任何阶段时，开发者至少核对：

- owner repo 是否正确，是否把别的 repo 的实现责任搬进本 repo；
- 是否改变了上游/下游 JSON contract、stable ID、fingerprint 或唯一事实源；
- 是否误把 Markdown、Zotero projection、handoff bundle 或 cache 提升成权威事实；
- 是否让 Stage 1 下载范围从 candidate item keys 意外扩大回 professor-wide；
- 是否让 preview / formal clustering / full-text resolved direction 的权威层级倒置；
- 是否让 Stage 3/5 回读被禁止的上游材料；
- 是否在没有真实用户选择时写入了选择状态；
- 是否同时维护 OpenCode 与 Codex 的业务等价语义，而不把 runtime-specific API 混成一套。

如果变更触及测试或验收，测试方法、证据和 merge gate 以 Project Consensus 为准；产品测试留在 producer repo，fixture 仓库只承担共享测试资产与隔离运行环境。
