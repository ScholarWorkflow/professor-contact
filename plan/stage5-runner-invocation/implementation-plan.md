# 第二批：解除 Stage 5 复制整份 runner 源码执行的机制（执行计划）

## 版本、来源与状态

- 需求来源：负责人 2026-10-18 在本仓库会话中给出的三批 Stage 重构要求，第 2 批原文：

  > 解除 Stage5 复制整份源码的机制，走常规审核。它目前把 contact_state.py 改写后复制到临时目录执行。之后若主脚本导入相邻模块，临时副本可能找不到这些模块。需要用明确的内部调用方式替代，同时保持审计标记、解释器、二次校验和写入顺序。这批影响实际执行机制，不能算纯搬文件。

- Requirement revision: 第 1 版（负责人 2026-10-18 授权的三批 Stage 重构要求第 2 批，原文见下）。
- Canonical Plan revision: 第 3 版。
- Target repository revision: `74bd29b572c1b3f68f230a554f57d0202e54cde8`（main）；工作分支 `refactor/stage5-runner-invocation` 从该提交拉出。
- Relevant upstream/runtime revision: N/A；不涉及外部仓库、代理入口或安装布局变化。被引用的已交付 Nix 计划见 [plan/nix-delivery/implementation-plan.md](../../plan/nix-delivery/implementation-plan.md)。
- Proposed review status: pending。
- 唯一规范来源：本文件。本文件只定义实施方案，不声明计划审核、测试审核或合并关口已经通过。

## 正式需求与范围

- **R1 解除复制**：`stage5_immutable.py` 不再读取整份 `contact_state.py` 源码、改写其中的审计标签后写入临时目录执行。
- **R2 明确内部调用**：改用 runner 自己提供的显式内部输入，由 runner 在它自己的安装位置执行。
- **R3 四项保持**：
  - **审计标记**：渲染 Markdown 里 ` ｜ 过稿: <来源>` 的取值语义与字节不变。
  - **解释器**：finalize 子进程仍以 `sys.executable` 启动同一批脚本，不改成进程内调用。
  - **二次校验**：wrapper 在提交 finalize 之前对审计标记契约的校验仍然存在，并在不一致时失败关闭。
  - **写入顺序**：`stage5-plan` → 草稿文件 → 映射文件 → 校验 → `stage5-finalize` 的顺序不变。
- **R4 动机**：runner 以后若 import 相邻模块，临时副本的 `sys.path[0]` 指向临时目录会找不到这些模块；本批要先解决，第三批（Stage3 纯渲染组抽成相邻模块）才能落地。

**非目标**：不改渲染正文、模板、state 与投影文件格式；不改公开 CLI 参数；不改 `stage5-plan` 的行为；不改 Nix 交付布局、入口清单与 `npm`/APM 安装路径；不做第三批的 Stage3 模块抽取；不新增任何用户目录写入；不引入锁、缓存或新的临时文件类型。

## 依据与关键事实

审核依据为项目 `PROJECT_CONSENSUS.md` 与 `Plan Reviewer Rule.md`；测试设计另按 `Test Engineer Rule.md` 审核。

| 决定 | 关键事实 | 来源 |
| --- | --- | --- |
| 复制只发生在 wrapper 一处 | 读整份 runner、`count(_PROVENANCE_NEEDLE) != 1` 校验、替换一次、写 `contact_state_stage5_immutable.py` 都在 `_runner_with_provenance`；全仓只有这一处改写 runner 源码 | `scripts/stage5_immutable.py:106-118`；`_PROVENANCE_NEEDLE` 定义在同文件 46 行 |
| 标签由 runner 拥有 | 渲染行在 `cmd_stage5_finalize` 的 per-variant 循环里，`过稿` 是硬编码字面量 `humanizer-ja(business)`，其余片段来自 `now_utc()`、`kind`、`profile_fingerprint`、`template_name`、`name_zh/name_ja` | `scripts/contact_state.py:10772-10777` |
| 标签只进 md | 同一标签所在 `lines` 只用于 `md_body`；`txt_body` 不含该行；state JSON 只记路径与 sha | `scripts/contact_state.py:10810-10811`、`10842-10861` |
| 直调 runner 无该参数 | `stage5-finalize` 的 parser 目前只有既有参数，`p.set_defaults(func=cmd_stage5_finalize)` | `scripts/contact_state.py:12709-12725` |
| 校验与失败码属于内部面 | 失败时打印 `{"status": "error", "reason_code": "stage5_provenance_patch_failed", "message": ...}`；仓库内没有测试或文档引用该失败码 | `scripts/stage5_immutable.py:177-184` |
| 复制副本的 `__file__` 是额外补偿的来源 | 注释与 `_child_env_with_checker` 都说明：临时副本的 `__file__` 在 scratch 目录，所以 checker locator 要从真实 runner 位置解析后经 `PROFESSOR_CONTACT_EVIDENCE_SCRIPT` 注入 | `scripts/stage5_immutable.py:121-136`、`185-190`（`env=` 在 189） |
| 真实 runner 的位置解析可用 | `upstream_check_script()` 从 `Path(__file__)` 解析相邻 `professor-collector` 安装位置；直接以真实脚本路径运行时不需要注入 | `scripts/contact_state.py:8974-8990` |
| 解释器契约已由 Nix 计划固定 | Nix 交付要求 wrapper 的 `sys.executable` 子进程与审计来源标签行为不变，只改薄入口 shebang | `plan/nix-delivery/implementation-plan.md:65` |
| 现有断言只看行为 | 测试断言 md 含 `过稿: none`、含 `过稿: humanizer-ja(dynamic-fields-only)`、不含 business；没有断言临时副本文件名、scratch 路径或失败码 | `tests/test_stage5_immutable.py:67-68`、`79-80`、`146` |
| 新增内部参数不破坏 CLI 契约测试 | 该测试只对 `stage5-plan`/`stage5-finalize` 断言 `--email-pack`、`--email-id` 存在、`--professor-dir` 不存在，不比对完整选项集合 | `tests/test_contact_state.py:4565-4570` |
| 产品文档描述了临时副本 | 生成器角色正文写“runs finalize through a temporary copy of the deterministic runner whose audit label is changed”，同段还含被测试断言的 `Do not pass --humanized or --humanized-map` 句 | `.apm/agents/professor-contact-email-generator.agent.md:232`；该断言在 `tests/test_stage5_dualtarget_contract.py:271-278` |
| 未支持的参数今天就会失败 | 调用方给 wrapper 传 `--audit-provenance` 今天不存在于任何 parser，会由 runner 的 argparse 以非零退出拒绝；因此它不是已支持输入 | `scripts/contact_state.py:12709-12725`；`scripts/stage5_immutable.py:139-193` |

## 方案

### 因果链

需求（runner 以后 import 相邻模块时，临时副本找不到它们）→ 现行机制（wrapper 读整份源码、盲替换审计标签、写临时副本、以 `sys.executable` 执行副本，副本的 `sys.path[0]` 是临时目录）→ 变更点（把“改写源码”换成 runner 自带的显式内部输入；wrapper 只做只读契约校验后直接执行真实 runner）→ 行为变化（finalize 子进程的脚本路径与 `sys.path[0]` 回到真实 `scripts/` 目录；不再产生临时 runner 文件；checker locator 由真实 `__file__` 解析）→ 满足需求（相邻模块可被 import，第三批具备前提）。

### 选定的调用方式（方案 A）

**改动一：runner 提供显式内部输入。** `contact_state.py` 的 `stage5-finalize` 增加内部参数 `--audit-provenance`，取值集合为 `business` / `none` / `dynamic-fields-only`，默认 `business`，并在帮助输出中隐藏（`argparse.SUPPRESS`）。渲染行末尾的 ` ｜ 过稿: …` 由该取值决定。

冻结的字节契约（三条后缀各自是完整字面量，含前导 ` ｜ 过稿: `）：

| 取值 | 渲染出的后缀 |
| --- | --- |
| `business` | ` ｜ 过稿: humanizer-ja(business)` |
| `none` | ` ｜ 过稿: none` |
| `dynamic-fields-only` | ` ｜ 过稿: humanizer-ja(dynamic-fields-only)` |

`business` 项必须与今天第 10775 行渲染出的字节完全相同；不带参数的直调路径保持 `business`，所以直调 runner 的 md 字节不变。

**改动二：wrapper 改为直调真实 runner。** `stage5_immutable.py`：

- 删除写临时副本的那一步，保留一次**只读**校验：读真实 runner 源码，若 `business` 后缀完整字面量出现次数不等于 1，则按现有失败形状打印 `{"status": "error", "reason_code": "stage5_provenance_patch_failed", ...}` 并返回失败。位置仍在写完草稿与映射之后、调用 finalize 之前。
- finalize 子进程改为 `[sys.executable, <真实 runner>, *clean, "--humanized-map", <map>, "--audit-provenance", <polish_mode>]`；`--polish-mode` 的合法取值与内部取值同名，映射是恒等映射。不传 `env=`，子进程继承环境。
- 删除 checker locator 注入（真实 `__file__` 已能解析），连带删除不再使用的导入。
- 调用方自带 `--audit-provenance` 时，wrapper 按既有处理 `--humanized`/`--humanized-map` 的方式丢弃该选项及其值，再追加自己的取值；不新增拒绝分支，也不把它透传给 runner。
- 保留的只读校验只检查 `business` 完整字面量：它保持的是现有二次校验的原意（渲染块里的旧标签仍是唯一可识别的字面量），另外两个取值由内部参数的 `choices` 在运行时兜底。不扩大成三条后缀的源码检查。
- wrapper 模块 docstring 与 `tests/test_stage5_immutable.py` 里描述“temporary copy”的注释同步改成“同一 runner 由内部参数选择审计来源”；测试逻辑本身不变。
- `stage5-plan` 子进程、草稿校验、映射写入、stdout/stderr 回放与退出码传递都不变。

### 冻结的契约

- 内部参数名与取值集合：`--audit-provenance` ∈ {`business`, `none`, `dynamic-fields-only`}，默认 `business`，不出现在公开帮助里。
- wrapper 的对照关系：`--polish-mode none` → `none`；`--polish-mode dynamic-fields-only` → `dynamic-fields-only`；不传 `--polish-mode` 等同 `none`。
- 失败关闭的触发条件与 JSON 形状不变；失败时 **wrapper 自身**不写用户文件：不调用 finalize、不写教授级 md/txt/state，草稿与映射只落在它自己的临时目录。`stage5-plan` 按既有顺序在标记校验之前运行，它可能触发上游 owner 的确定性本地证据重建并写 `<program_root>/教授研究/_联系方式证据.json`；那是既有行为（今天用临时副本时同样发生），不由标记校验失败触发，也不由本批引入。绝对化的“失败前用户目录零写入”与“保留 plan 在前的既有顺序”不能同时成立，本计划只承诺前者被限定后的版本。
- 写入顺序、解释器、stdout/stderr 回放顺序、退出码传递不变。
- `PROFESSOR_CONTACT_EVIDENCE_SCRIPT` 的解析规则不变：显式设置时优先，未设置时由真实 runner 位置解析。

### 替代方向与取舍

| 方向 | 不采用的原因 |
| --- | --- |
| 进程内 import runner 后修改模块常量，再调用 finalize 函数 | 取消 finalize 子进程，需要手工映射 `fail()`/`soft_exit()`/argparse 的退出码与 stdout 缓冲；相邻模块 import 时还要临时维护 `sys.path`；解释器与进程语义都与现在不同，回归面更大 |
| 用环境变量传审计来源 | 隐式全局状态，容易泄漏到嵌套调用，测试隔离更麻烦；不如显式参数可审计 |
| 保留复制，把相邻模块一起复制到临时目录 | 不解决根因；以后每新增一个相邻模块都要扩大复制面，且副本与真实安装的模块身份会分叉 |
| 让 wrapper 直接渲染并替换 md 文本 | 会把渲染 owner 从 runner 挪到 wrapper，改变 state/sha 归属，超出本批范围 |

## 影响

- **intended_change**：finalize 的审计来源由 runner 的显式内部输入决定；wrapper 不再改写 runner 源码，也不再写临时 runner 副本；checker locator 改由真实脚本位置解析。
- **preserved_behavior**：直调 `contact_state.py stage5-finalize` 的渲染字节（含 business 标签）；wrapper 默认与 `--polish-mode dynamic-fields-only` 两种输出的标签与模板保护；`stage5-plan`、草稿校验、映射写入、stdout/stderr 回放、退出码；plan 阶段的上游证据检查与确定性本地重建行为（含它可能写 `<program_root>/教授研究/_联系方式证据.json`）；`--humanized`/`--humanized-map` 仍被 wrapper 忽略；`--email-id` 定向范围；`PROFESSOR_CONTACT_EVIDENCE_SCRIPT` 的解析优先级与临时目录清理。
- **approved_behavior_change**：无。本批不改变任何已支持输入的行为：新参数只出现在内部通道，公开 CLI 与 `--polish-mode` 语义不变；wrapper 对旧参数的处理方式不变。具体依据与残留差异见下节“失败路径说明”。
- **prohibited_side_effect**：改写渲染正文、模板、state/投影 sha；改动公开 CLI 或新增公开参数；把 finalize 改成进程内调用；改变解释器选择与安装布局；在失败路径写用户目录；为测试方便修改 owner 或产品契约。
- **unresolved impact**：无影响方案成立的项目。两项已记录的残留差异（见“失败路径说明”）都不改变正式 requirement、owner、核心机制、兼容约定或正式可观察业务结果；仓库外是否有人解析临时副本文件名属于未知但非 contract 的事项，方案不依赖该事实。

### 失败路径说明（不构成已支持行为的变更）

1. 调用方给 wrapper 传 `--audit-provenance`：今天该名字不存在于任何 parser，会被 runner 的 argparse 以非零退出拒绝；本批之后由 wrapper 直接丢弃并按 `--polish-mode` 追加取值，调用不再到达 runner 的同名未知参数分支。可观察差异是这次调用的结果从“报错”变成“按 wrapper 声明的 polish 取值成功”，涉及的是从未支持的输入名，不是已支持行为。
2. 失败文案中的脚本名：今天 finalize 子进程是临时副本，argparse usage/错误里可能出现 `contact_state_stage5_immutable.py`；本批之后固定为真实 `contact_state.py`。失败 JSON 的 `status`/`reason_code`/`message` 字段与退出码传递都不变。
3. `stage5_provenance_patch_failed` 这个原因码沿用旧字符串：它本来就不是正常流程的一部分，本次不改名，避免调用方多一处差异。

## 关键安全条件与反例

必须一直成立的条件：

1. 直调 runner 不带内部参数时，渲染出的 md 与今天逐字节相同。
2. wrapper 三种 polish 取值下的标签取值与今天相同。
3. `business` 后缀完整字面量在 runner 源码中恰好出现一次；否则 wrapper 在调用 finalize 之前失败关闭，且除 plan 阶段既有的上游证据重建外不写用户文件。
4. finalize 子进程仍由 `sys.executable` 启动，且执行的是真实脚本路径（`sys.path[0]` 为真实 `scripts/` 目录）。
5. 写入顺序仍是 plan → 草稿 → 映射 → 校验 → finalize。
6. 已安装布局（`professor-collector` 与 `professor-contact` 为 sibling skill）下，finalize 仍能解析到 `contact_evidence.py`；显式设置的 `PROFESSOR_CONTACT_EVIDENCE_SCRIPT` 仍然优先。

代表性反例：

- runner 的 `business` 标签被拆成多段拼接，字面量计数变成 0：wrapper 在调用 finalize 之前失败关闭并返回既有失败码；不写教授级 md/txt/state，也不产生临时 runner 副本。
- 程序根里 `教授研究/_联系方式证据.json` 缺失或其内容变化：plan 阶段的 `resolve_contact_evidence` 会按既有契约跑上游确定性本地重建并写该文件（`cmd_stage5_plan` 9981、重建入口 `run_contact_evidence_rebuild` 9017），随后即使标记校验失败，这次写入也不会被撤销。该路径在今天的临时副本机制下同样存在、顺序也相同，因此本批既不放宽也不收紧它；计划因此只承诺 wrapper 自身零写入，不承诺整个调用链零写入。
- 调用方显式传 `--audit-provenance business`：wrapper 丢弃该选项，按自己声明的 polish 取值（不传时为 `none`）渲染；调用方的取值不得覆盖 wrapper 的声明。
- 同一进程并发调用 wrapper：每次调用各自建临时目录，只有草稿与映射写入其中，互不共享路径。
- 真实 runner 与 wrapper 不在同一目录（测试把两者复制到安装布局再执行）：wrapper 以自身相邻的 runner 路径调用，行为与今天一致。

## 实施位置与顺序

1. **计划审核**：本文件取得 `Plan conclusion: APPROVED`。
2. **本地执行代理**（按获批计划实施）：
   - `scripts/contact_state.py`：新增内部参数与后缀映射，渲染行改用映射值；不新增公开参数。
   - `scripts/stage5_immutable.py`：删除副本写入与 checker 注入，改为只读契约校验后直调真实 runner；同步模块 docstring 里“executes a temporary copy”的表述；保留原有参数处理、错误形状、回放与退出码。
   - `tests/test_stage5_immutable.py`：同步 185-188 与 206-208 处描述临时副本的注释；本批新增用例见 `test-plan.md`。
   - `.apm/agents/professor-contact-email-generator.agent.md`：把“临时副本改写审计标签”的表述改成“同一 runner 由内部参数选择审计来源”，必须保留同段被测试断言的 “Do not pass `--humanized` or `--humanized-map`” 句与 `dynamic-fields-only` 字样。
   - `plan/nix-delivery/implementation-plan.md`：只在第 65 行附近追加一条带日期的说明，指出临时 provenance 副本已由内部参数取代，而同一解释器、checker 解析、临时目录清理、错误传播与审计来源标签的要求仍然有效；不改写该已交付计划的其余内容。
3. **测试准备与审核**：测试工程师按 `Test Engineer Rule.md` 准备测试资产（见同目录 `test-plan.md`）。
4. **正式执行**：测试计划获批后执行受影响测试并记录结果；未受影响的通过结果沿用。

## 修订记录

- 第 1 版：首次提交计划审核。
- 第 2 版：按第 1 轮计划审核的 P3 blocker 修正影响栏——取消“新增拒绝行为”的设计，调用方自带的内部参数改为按既有 `--humanized` 方式丢弃；把残留可观察差异移入“失败路径说明”，`approved_behavior_change` 记为无，并更正 `tests/test_stage5_dualtarget_contract.py` 与 `stage5_immutable.py` 的引用位置。同时合入非阻断观察：模块 docstring 与测试注释同步、只读校验范围的取舍说明、失败文案中的脚本名差异。P1/P2/P4 与 owner、核心机制、冻结契约均未变化。
- 第 3 版：按正常审核提出的“失败时零写入承诺不成立”修正：把“失败时不得改写任何用户文件”限定为 wrapper 自身零写入，并在冻结契约、安全条件、preserved_behavior 与反例中明确写出 `stage5-plan` 按既有顺序可能触发上游确定性本地证据重建、写 `<program_root>/教授研究/_联系方式证据.json`（`cmd_stage5_plan` 9981 → `run_contact_evidence_rebuild` 9017）；该路径在今天的临时副本机制下同样存在，本批不放宽也不收紧。同步修正测试计划对 T3 的表述。P1/P2 与 owner、核心机制、冻结契约其余内容未变；P4 的改动清单未变。

## 审核状态

计划第 3 版为当前唯一计划。第 1 轮结论 `NEEDS_MODIFICATION`（仅 P3 一项 blocker）已按第 2 版修正并取得 `APPROVED`；第 3 版只修正“零写入”承诺的适用范围与相应记录，未改方案、owner 与冻结契约。后续审核以本文件、需求原文、`PROJECT_CONSENSUS.md` 与 `Plan Reviewer Rule.md` 为输入。
