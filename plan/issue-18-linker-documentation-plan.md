# 第 79 号拉取请求：撤销虚列的论文补链命令——实施计划 v1.0

> **唯一有效计划**：本文件，保存于 `ScholarWorkflow/professor-contact` 的 `plan/`。本次及后续获批实施均使用现有 [PR #79](https://github.com/ScholarWorkflow/professor-contact/pull/79) 的 `docs/issue-18-remove-phantom-linker` 分支，不另建拉取请求。
>
> **Proposed review status: pending**。本文件不声明计划已批准、产品测试通过或可以合并；拉取请求继续保持草稿。

## 一、版本与依据

| 项目 | 版本或位置 |
| --- | --- |
| Requirement revision | [paper-analysis 第 18 号问题](https://github.com/ScholarWorkflow/paper-analysis/issues/18)，2026-10-11 需求收缩版本，读取时更新于 2026-10-11T14:33:39Z |
| Plan revision | 本文件 v1.0，2026-10-11；首次建立，无历史计划要拼接 |
| Target repository revision | `professor-contact` 基线 `41aa5f4a3587bdbb7ea31342c7a5a5d39224f4ed`；本 PR 原提交 `36afd24d16c3cc50e427238f08c91a7d456601f3`；链接来源说明补正提交 `0ac4808888df0a14e9f2bd4ec023e75d243d284d` |
| Relevant upstream revision | `paper-analysis@19eb3e26e8eb7ec60cba1d74efe0f27534c10203`；其 [PR #19](https://github.com/ScholarWorkflow/paper-analysis/pull/19) 仅记录已收缩需求，不作为此仓库新增实现的授权 |
| Runtime authority | [Codex 技能文档](https://developers.openai.com/codex/skills)，2026-10-11 查阅；本仓库主技能文档前部的运行时路由规则 |
| 项目规则 | [Project Consensus](https://app.notion.com/p/3d60101a85f3815a8c43f271f2b4d91d)、[Plan Reviewer Rule](https://app.notion.com/p/3e80101a85f3817a94cbc6eca1a76a5c)、[Test Engineer Rule](https://app.notion.com/p/3d80101a85f380d8a8f5ce528141e253) |

**版本使用原则**：上述提交编号是核查依据，并非今后实施时必须回退的提交。实施者从现有 PR 分支当时的最新提交开始；如果此后需求、代码或相关上游约定改变，先核对语义影响，仅修订受影响部分。

## 二、已确认需求与非目标

本次只有一个产品文档目标：让 `.apm/skills/professor-contact/SKILL.md` 的论文引用说明与**实际交付的功能**相符，取消要求代理调用从未交付的论文链接维护技能和命令；保留现有阶段二、阶段三的链接渲染及原引用格式。

**必须保留的行为**：

1. 阶段二现有论文引用及论文一览按 `item_key` 与已有 `analysis_file` 生成 Zotero／本地分析链接；无真实分析路径时不编造路径。
2. 阶段三只读 `套磁候选输入.json`，由其 `papers[item_key].analysis_file` 渲染支撑论文的分析链接；不得为了链接重新读取 `论文分析/_index.json`。该索引是阶段二记录分析文件的地方。
3. 其他 Markdown 写入方只有取得确切分析路径才追加本地 `[分析]` 链接；原有 Zotero 链接格式及邮件正文禁链约定不变。
4. Codex 与 OpenCode 各自遵守当前主技能文档前部的原有运行时路由；本任务不改变任何代理委派、安装、提示词传递、状态或数据格式。

**明确撤销和禁止的工作**：不创建 `paper-analysis-linker`、`paper-analysis-link` 或其独立安装入口；不实现 `--backfill`、`--map`、`--dedup`、预览回填、批量改写既存 Markdown、对账报表、重名文件清理／迁移／隔离恢复；不以此为由修改 `paper-analysis`、`contact_state.py`、`_stage2_chatgpt_handoff_impl.py`、索引、分析文件、证据附属文件、任一阶段的结构化状态或套磁邮件；不新增任何已取消功能的产品测试、专用夹具、冒烟测试或安装验收。

以上来自第 18 号问题中用户于 2026-10-11 批准的需求收缩；本文不得恢复旧版本任务。

## 三、关键事实、职责和方案决定

### 3.1 正式要求与实际代码

| 决定 | 正式要求（应当怎样） | 现状证据（现在怎样，限定已核对版本） |
| --- | --- | --- |
| D1：撤销独立补链工具声明 | 第 18 号问题明确不开发或验收未实现的工具 | `paper-analysis@19eb3e26` 仓库树仅有 `.apm/skills/paper-analysis` 及既有分析脚本；`pyproject.toml` 没有链接命令入口；不能从旧调用方文档推断工具存在 |
| D2：保留阶段二现有链接 | 第 18 号问题要求不改已实现链接行为 | `contact_state.py` [`citation_render`（L4134–4147）](https://github.com/ScholarWorkflow/professor-contact/blob/36afd24d16c3cc50e427238f08c91a7d456601f3/.apm/skills/professor-contact/scripts/contact_state.py#L4134-L4147) 和[论文一览（L4360–4375）](https://github.com/ScholarWorkflow/professor-contact/blob/36afd24d16c3cc50e427238f08c91a7d456601f3/.apm/skills/professor-contact/scripts/contact_state.py#L4360-L4375) 已渲染真实链接；[`_stage2_chatgpt_handoff_impl.py`（L551–611）](https://github.com/ScholarWorkflow/professor-contact/blob/36afd24d16c3cc50e427238f08c91a7d456601f3/.apm/skills/professor-contact/scripts/_stage2_chatgpt_handoff_impl.py#L551-L611) 写入索引 `papers[item_key].file` |
| D3：澄清阶段三路径来源 | 主技能自身规定阶段三只读输入包；不得让链接说明要求回读索引 | [`contact_state.py`（L7360–7390）](https://github.com/ScholarWorkflow/professor-contact/blob/36afd24d16c3cc50e427238f08c91a7d456601f3/.apm/skills/professor-contact/scripts/contact_state.py#L7360-L7390) 从输入包论文的 `analysis_file` 生成 `_analysis_rel`；[L6950–6970](https://github.com/ScholarWorkflow/professor-contact/blob/36afd24d16c3cc50e427238f08c91a7d456601f3/.apm/skills/professor-contact/scripts/contact_state.py#L6950-L6970) 写支撑论文表格 |
| D4：仅纠正调用方说明 | 此次改动 owner 是 `professor-contact` 文档，不批准跨仓库新技能 | [Codex 官方技能文档](https://developers.openai.com/codex/skills)规定技能由 `SKILL.md` 宣告并供原生发现或调用；没有把历史文档里的 `skill(name: ...)` 或虚列的 `paper-analysis-link` 声明成 Codex 内建命令。本仓库运行时路由已在主技能开头单独规定 |
| D5：不增加产品测试 | 第 18 号问题已取消虚列命令的测试要求；测试规则只允许检查本次明确改变的业务行为 | 现有 PR 修改的是 `SKILL.md` 的调用方叙述，未触及程序或安装入口；无需为了取消命令要求启动 Codex、OpenCode、评估服务或下载论文 |

D1 的“不存在”结论仅对已读取的 `paper-analysis@19eb3e26` 仓库树、构建配置与 `professor-contact` 相应调用约定成立；不主张其他所有版本、仓库或历史都不存在同名代码。若实施时发现实际已交付的同名入口，记录其完整仓库、提交与调用方，按正式需求重新判断，不能单凭名称恢复已撤销任务。

### 3.2 因果链、owner 与替代方向

**问题**：原调用方文档把未交付的维护命令当作可执行依赖，还把所有阶段的链接路径统一描述成直接读取索引。**实际原理**：Codex／OpenCode 代理读取技能说明决定后续动作；阶段二已有索引和引用渲染，阶段三实际消费前阶段输入包。**修改位置**：只改 `professor-contact/SKILL.md`「论文引用链接约定」下的现有条款。**效果**：代理不再被要求安装或调用虚列工具，也不在阶段三为补链回读索引；现有链接输出和状态写入保持原样。**需求满足**：调用文档如实描述既有能力，不暗中新增产品功能。

文档错误由 `professor-contact` 负责；`paper-analysis` 只维护其已经交付的论文分析入口；各阶段实际链接仍由 `contact_state.py` 既有调用路径负责；本次禁止让测试夹具、外部安装脚本或别的仓库替 `professor-contact` 补偿。

**采用方案**：就地删除虚列命令要求，并把「有分析文件」的路径来源分别写清楚。**未采用的方案**：新建独立链接维护工具会恢复用户已撤销的开发和测试范围；删除整节链接约定会丢失仍在使用的 Zotero 与分析链接规则；无条件迁移真实渲染程序到 `paper-analysis` 缺少已获批准的目标调用方。三者均不采用。

## 四、影响与安全条件

- `intended_change`：主技能文字只描述已存在的链接渲染与正确的阶段输入来源，明确禁止虚列工具调用。
- `preserved_behavior`：阶段零至五、程序级／教授级数据、索引与引用格式、Codex／OpenCode 委派、现有业务产物、邮件禁链约定、旧状态兼容都保持不变。
- `approved_behavior_change`：第 18 号问题 2026-10-11 用户批准**撤销**原额外工具和相关测试任务；没有批准更改产品运行行为。
- `prohibited_side_effect`：不批量改写旧文件、不删除或移动论文、不修改业务代码、不安装未交付的命令、不重新采样业务测试、不更改 GitHub 其他分支或新开 PR。
- `unresolved impact`：无已发现的关键未决项。其他仓库未来是否需要批量补链属于新需求，不能借本 PR 决定。

必须维持的约束与现实反例：

| 输入或情境 | 必须保持的结果 |
| --- | --- |
| 阶段二某论文有已登记分析路径 | 原链接位置仍生成 Zotero 链接和相对 `[分析]` 链接 |
| 论文没有分析路径或教授没有分析目录 | 只保留既有 Zotero 引用；不猜测分析路径、不调用回填 |
| 阶段三输入包有 `analysis_file`，但代理不能访问索引 | 照输入包渲染；本次文字不创造对 `_index.json` 的阶段三依赖 |
| 不同教授或方向引用同名论文 | 现有 `item_key` 与教授目录归属保持不变；文档修改不改变任何身份映射 |
| 需要修订历史 Markdown／清理重复文件 | 本次不执行；既有已保存的用户材料原样保留 |
| Codex 代理读到已修订主技能 | 依原有 Codex 路由调用已安装的正式代理；不会为链接维护转去使用 OpenCode 专属语法、命令探测或新命令 |
| OpenCode 代理读到已修订主技能 | 原有 Task 路由不变；同样不调用虚列维护工具 |

因为没有程序代码、数据字段或生命周期操作变更，迁移、回滚数据、锁、并发控制、错误重试及清理程序均不适用。文档更正可单独撤回，不能据此回滚既有业务资料。

## 五、本地代理执行顺序（后续都在 PR #79 分支）

**步骤 1：取得准确源分支。** 在独立的 `professor-contact` 源仓库进入 `docs/issue-18-remove-phantom-linker`，不要在 `worktrees/` 或 `apm-consumers/` 当成生产者编辑；不要基于主分支另开分支。先查看当前分支与提交：

```sh
git fetch origin docs/issue-18-remove-phantom-linker
git switch docs/issue-18-remove-phantom-linker
git pull --ff-only origin docs/issue-18-remove-phantom-linker
git status --short
git rev-parse HEAD
```

仓库已安装、工作区有其他修改或分支前进时先辨认本次目标，不能覆盖别人的更改。首次本地没有同名分支时，从远端同名分支建立本地跟踪分支；仍不得创建新的 PR 分支。

**步骤 2：对照需求和源码。** 阅读第 18 号问题的当前正文、本计划、`SKILL.md`「论文引用链接约定」和文件开头的运行时路由；抽查上述 `contact_state.py` 与阶段二索引写入点。只在关键行为事实或宿主用法有争议时重查对应版本官方资料，避免顺带审核整套运行时。

**步骤 3：确认并保留既有修改。** PR 原提交已经删去 `--backfill`、`--map`、`--dedup` 的调用与安装前置。其后在相同分支修正「有分析文件」的阶段来源说明，明确阶段三只读 `套磁候选输入.json`；将“无独立工具”的事实限定在核对版本。不要把旧命令重新写回执行指令。遇到相同语义的新增文本，只修订该段；不改 `SKILL.md` 其他阶段的业务契约。

**步骤 4：人工检查最终差异。** 确认：
- 已不存在要求执行 `skill(name: "paper-analysis-linker")`、`paper-analysis-link` 或 `--backfill`／`--map`／`--dedup` 的正面步骤；作为“禁止调用”的说明可以保留名称。
- `citation_render`、阶段二论文一览、阶段三支撑论文路径来源均符合已核对源代码；阶段三没有新建索引读取义务。
- Zotero／分析链接格式、无文件时保持原样、聊天及套磁邮件禁链边界未删除。
- 产品脚本、依赖清单、已有测试、索引与资料文件不在本次差异中。

可用 `git diff --check` 做文档空白和补丁格式检查，`git diff -- .apm/skills/professor-contact/SKILL.md plan/issue-18-linker-documentation-plan.md` 查看内容。**这是对提交内容的人工核对，不增列产品测试用例或运行时验收。**

**步骤 5：提交与推送。** 本 PR 只提交链接约定文档及 `plan/` 下本计划等必要审核记录。仅向 `docs/issue-18-remove-phantom-linker` 推送；不修改 `main`、不新开 PR、不合并、不擅自转为准备审核状态。PR 描述和评论引用本计划当前版本及实际提交号，不在评论粘贴第二套完整方案。

**步骤 6：交接。** 记录正式需求版本、计划版本、分支的实际提交号、改动文件和文档差异检查结果；注明没有实施新工具、没有运行产品测试、Plan 尚待正式审批。若之后另有获批的代码工作，也必须先修订本文件中的目标范围、责任和必要测试上限，再继续使用本 PR 分支。

## 六、测试范围与结果标注

依据第 18 号问题及 `Test Engineer Rule`，**本次必测产品清单为空**：没有新功能、没有产品行为改变、没有新的安装产物。因此不安排安装／重装干净消费者、Codex／OpenCode 冒烟、评估服务、回填／对账／去重测试、夹具建设或全仓回归。

实施者只需人工核对第五码步骤中的文档差异及补丁格式，并记录“文档核对完成／未完成”；不得把该记录写成“产品测试通过”。如果后续获批改变真实业务行为，应先由验收决定人确认新必测目标，再按测试工程师规则在同一 `plan/` 中修订唯一有效计划，未获授权不能扩测。

## 七、停止条件及提交边界

若第 18 号问题需求再变、发现与 D1–D4 相冲突的已交付同名工具、阶段三输入源实际发生变化，或有人要求代码层面新增链接维护能力：**停止受影响的实施项**，记录具体提交和行为证据并修订需求／计划，不能由本地代理擅自扩大。

交付边界为：一份反映事实的 `SKILL.md`、本文件、以及同一 PR 分支上的相应提交。计划批准与否交正式 reviewer 在 Review record 中裁定；草稿 PR 不因此自动合并。
