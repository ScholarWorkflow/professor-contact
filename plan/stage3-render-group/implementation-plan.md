# 第三批：把 Stage 3 纯渲染组抽成独立模块（执行计划）

## 版本、来源与状态

- 需求来源：负责人 2026-10-18 在本仓库会话中给出的三批 Stage 重构要求，第 3 批原文：

  > 抽 Stage3 纯渲染组，可作为后续快审候选。六个相关函数可以组成一个自然模块，不必每个函数开 PR。前提是第二批解决导入问题，并保持渲染结果逐字一致、时间依赖和旧调用接口不变。不要顺便改 Markdown 格式，因为结果还用于摘要绑定和校验定位。

- Requirement revision: 第 1 版（三批要求第 3 批）。
- Canonical Plan revision: 第 1 版。
- Target repository revision: `ffa91aedf94aaf146f9cf1899f3fe4395cfaddad`（分支 `refactor/stage5-runner-invocation`，含第二批改动）；本批工作分支 `refactor/stage3-render-group` 从该提交拉出。
- Implementation sequencing prerequisite: 第二批 PR #97 尚未合并。本批按堆叠分支交付，合并顺序 #97 → 本批；#97 一旦改写，本批按受影响范围重放并重跑受影响检查。
- Relevant upstream/runtime revision: N/A；不涉及外部仓库、代理入口、安装布局或 CLI 变化。
- Proposed review status: **APPROVED**（`Plan conclusion: APPROVED`，P1–P4 全 PASS；独立计划审核于 2026-10-18/19 给出）。
- 唯一规范来源：本文件。本文件只定义实施方案，不声明计划审核、测试审核或合并关口已经通过。

## 正式需求与范围

- **R1 抽组**：把 `_red_line_key`、`_candidate_red_lines`、`_render_idea_block`、`_stage3_scope_marker`、`render_candidates_md`、`render_candidates_overview` 六个函数移到一个独立模块；不按函数拆成多个 PR。
- **R2 渲染逐字一致**：相同输入产生逐字节相同的 Markdown；不改 Markdown 格式。
- **R3 时间依赖不变**：渲染里的时间戳仍来自 runner 的 `now_utc()`——同一个函数、同一个调用位置、同样格式。
- **R4 旧调用接口不变**：`contact_state.render_candidates_md` 与 `contact_state.render_candidates_overview` 仍以原名、原签名、原行为可用；runner 内两个既有调用点不改。
- **R5 前提**：第二批已解除“改写并复制整份 runner 到临时目录执行”，runner 现在以自己的路径执行，可以加载相邻模块。

**非目标**：不改渲染正文、模板或 Markdown 格式；不改 sha 绑定、校验定位或 state/投影文件；不改 CLI 与七个入口；不移动共享错误通道、事务／回滚、Stage3 提交与校验交接、Stage4/5 证据处理（这些属常规审核的其他批）；不重命名或合并现有函数；不改任何测试断言与测试名称。

## 依据与关键事实

审核依据为项目 `PROJECT_CONSENSUS.md` 与 `Plan Reviewer Rule.md`；测试设计另按 `Test Engineer Rule.md` 审核。

| 决定 | 关键事实 | 来源（目标修订） |
| --- | --- | --- |
| 六个函数现在是一个连续块 | `_red_line_key` 7465-7466、`_candidate_red_lines` 7469-7485、`_render_idea_block` 7488-7550、`_stage3_scope_marker` 7553-7554、`render_candidates_md` 7557-7628、`render_candidates_overview` 7631-7651 | `scripts/contact_state.py` |
| 组外只有一个调用点各一处 | `render_candidates_md` 在 `cmd_stage3_finalize` 7973 调用；`render_candidates_overview` 在 `cmd_stage3_rebuild_overview` 8100 调用；四个私有 helper 只被组内调用 | 同上 |
| 全仓没有外部调用者 | 仓库内除 `contact_state.py` 外，没有任何文件引用这六个名字（一个同名方法是测试类自己的方法） | 全仓检索 |
| 组内需要的模块级名字只有四个 | 自由名字：`json`、`re`、`now_utc`、`CANDIDATES_MD`，另有注解用到的 `Path` | 对 AST 的自由变量分析（脚本与结果见测试记录） |
| 渲染结果用于 sha 绑定 | `body = render_candidates_md(...)` 之后 `body_sha = sha256_text(body)` 写入 state；总览同理 | `scripts/contact_state.py:7981`、`8113` |
| 渲染结果用于校验定位 | `stage3_render_line_scopes(md_text)` 按渲染文本的行与 `<!-- stage3_scope: ... -->` 标记定位校验范围；标记由 `_stage3_scope_marker` 生成 | `scripts/contact_state.py:5716`、`5708`、`7553-7554` |
| 相邻模块的既有加载做法 | `stage2_chatgpt_handoff.py` 用 `Path(__file__).with_name(...)` + `spec_from_file_location` + `module_from_spec` + `exec_module` 加载同目录 `_stage2_chatgpt_handoff_impl.py`，并把被移动的名字放回自己的命名空间 | `scripts/stage2_chatgpt_handoff.py:41-50` |
| 按文件路径加载 runner 时没有 `scripts/` 在 `sys.path` | 测试用 `spec_from_file_location("contact_state", <skill>/scripts/contact_state.py)` 直接执行 runner；因此相邻模块必须按路径加载，不能依赖普通 `import` | `tests/test_contact_state.py:24-29` 等 |
| 有测试夹具会把 runner 复制到别处 | 假安装布局夹具把 `contact_state.py`（与 wrapper）复制进 `.agents/skills/professor-contact/scripts/` | `tests/test_stage5_immutable.py:210-222`、`tests/test_stage5_dualtarget_contract.py:327-331` |
| 没有测试 monkeypatch `now_utc` | 测试里 `now_utc` 只以 `contact_state.now_utc()` 形式出现，无 `patch`、无赋值 | 全仓测试检索 |
| Nix 交付按整树复制 scripts 目录 | runtime 派生把 `.apm/skills/professor-contact/` 整棵树复制，只改七个薄入口的 shebang；新模块随之进入安装 | `nix/contact.nix:119-152` |
| 内部辅助模块不需要进公开入口清单 | `SKILL.md` 的七个入口清单与 `nix/contact.nix` 的 `entryNames` 只列薄入口；`_stage2_chatgpt_handoff_impl.py` 同样不在清单里，也没有文档枚举它 | `SKILL.md:170`、`nix/contact.nix:120-131` |

## 方案

### 因果链

需求（Stage 3 纯渲染可以独立成模块）→ 现行机制（六个函数在 `contact_state.py` 内成块，只被同文件两处调用；渲染结果被 sha256 绑定进 state、并被校验定位按行解析）→ 变更点（按行区间原样搬到新的内部模块；runner 用仓库已有的按路径加载做法加载它，并把时钟与文件名常量作为显式关键字参数注入；runner 保留同名同签名的两个公开入口）→ 行为变化（用户可见渲染与绑定完全不变；runner 命名空间通过模块对象取得实现；新增一个内部模块文件）→ 满足需求。

### 选定设计

**新模块 `scripts/_stage3_render.py`**（下划线前缀沿用既有内部辅助模块约定，与 `_stage2_chatgpt_handoff_impl.py` 一致）：文件头 `from __future__ import annotations`、`import json`、`import re`、`from pathlib import Path`；六个函数按目标修订的行区间**原样**搬入，只对两个公开渲染器追加关键字参数：

- `render_candidates_md(..., cross_groups=None, *, now_utc)`；
- `render_candidates_overview(entries, program_root, cross_groups=None, *, now_utc, candidates_md)`。

四个私有 helper 的签名与函数体逐字不变。模块不 import runner，也不定义第二份时钟。

**runner 侧加载**：沿用 `stage2_chatgpt_handoff.py:41-50` 的既有做法——`Path(__file__).with_name("_stage3_render.py")`、`spec_from_file_location`、`module_from_spec`、`exec_module`；不修改 `sys.path`，不注册 `sys.modules`。

**runner 侧入口**：

- 保留 `render_candidates_md(professor, category, direction_entries, profile_fp, state_fingerprint, professor_dir, cross_groups=None)` 与 `render_candidates_overview(entries, program_root, cross_groups=None)` 两个同名同签名函数，转调模块并传入 `now_utc=now_utc`（总览另传 `candidates_md=CANDIDATES_MD`）。
- 四个私有 helper 以别名保留在 runner 命名空间（与既有“保留模块级 API，包括被测试的私有 helper”的做法一致）。
- `cmd_stage3_finalize`（7973）与 `cmd_stage3_rebuild_overview`（8100）两个调用点不改。

**测试夹具同步**：把 runner 复制进假安装布局的两个夹具必须同时复制 `_stage3_render.py`，否则复制出来的 runner 在导入阶段就找不到相邻模块。

### 冻结的契约

- 六个函数的函数名、参数（除两个新增的关键字注入）与输出字节不变；Markdown 格式、标记文本、行布局都不变。
- `contact_state.render_candidates_md` / `contact_state.render_candidates_overview` 的公开签名与行为不变；两个调用点不做改动。
- 时间戳仍由 runner 的 `now_utc()` 在渲染函数内部读取。
- 新模块是内部辅助模块：不进七个入口清单，不改 `entryNames`，不改任何 CLI。
- 失败与错误通道不变：本批不移动 `fail` / `soft_exit` / 业务通道，渲染函数仍不自行抛新异常。

### 替代方向与取舍

| 方向 | 不采用的原因 |
| --- | --- |
| 让新模块 `import contact_state` 取 `now_utc` 与 `CANDIDATES_MD` | 循环导入；测试按文件路径加载 runner，`contact_state` 不一定在 `sys.modules` |
| 新模块自定义一份 `now_utc` | 出现第二个时钟实现，直接违反 R3；格式或时区漂移不会被现有测试发现 |
| runner 把 `scripts/` 插进 `sys.path` 后普通 `import` | 改变全局导入路径，可能遮蔽同名模块，并让加载行为依赖调用方环境 |
| 加载后给模块属性赋值（`module.now_utc = now_utc`） | 隐式全局状态，函数签名上看不到依赖，模块无法独立测试 |
| 把 Stage3 渲染连同校验/交接一起搬 | 校验定位、提交顺序与异常类型属常规审核的其他批，混做会改变共享状态 |
| 只把两个公开函数搬走，私有 helper 留原地 | 私有 helper 只服务这组渲染，留在 runner 里仍然占用 runner 体积，且不构成自然模块 |

## 影响

- **intended_change**：Stage 3 纯渲染组移入内部模块 `_stage3_render.py`；runner 以按路径加载的方式引入它，并以两个同名同签名入口对外保持原 API；两个复制 runner 的测试夹具同步复制新模块。
- **preserved_behavior**：渲染字节（含 `now_utc()` 时间戳、`<!-- candidate_meta -->`、`<!-- stage3_scope -->` 标记、表格与行列布局）；sha 绑定与校验定位；`stage3-finalize` 与 `stage3-rebuild-overview` 的 CLI 与写入结果；`stage3_render_line_scopes` 的解析结果；七个入口与 Nix 安装布局；错误通道与退出码。
- **approved_behavior_change**：无。运行期没有任何已支持输入的行为变化；新增的只有一个内部模块文件与它的按路径加载。
- **prohibited_side_effect**：修改 Markdown 格式或标记文本；改动 sha 绑定与校验定位；改动 CLI、入口清单或安装布局；在模块里复制时钟或常量；把校验/交接/证据处理一并搬动；在 runner 里改 `sys.path`；改测试断言。
- **unresolved impact**：无影响方案成立的项目。仓库外若有人按脚本目录全量列举文件（例如自定义打包脚本），会多看到一个内部模块；这属于预期内的新增文件，不改变入口契约。

## 关键安全条件与反例

必须一直成立的条件：

1. 相同输入与冻结时钟下，六个函数的输出与改动前逐字节相同。
2. runner 无论以脚本方式直接执行，还是被测试按文件路径加载，都能按路径加载到 `_stage3_render.py`。
3. 任何把 runner 复制到别处的夹具，必须同时复制 `_stage3_render.py`。
4. `contact_state.render_candidates_md` / `render_candidates_overview` 的签名与行为不变，两个调用点不改。
5. 渲染文本的标记与行布局不变，`stage3_render_line_scopes` 的定位结果不变。
6. 时钟仍只有一个来源（runner 的 `now_utc`）。

代表性反例：

- 夹具只复制 runner：复制出的 runner 在导入阶段失败——必须同步复制（由测试覆盖）。
- 新模块里再写一份时间格式：冻结时钟的逐字节对比会发现差异；不得以“格式看起来一样”放行。
- 有人在被测进程里 monkeypatch `contact_state.now_utc`：转调时传入的是当时的 `now_utc` 对象，包装函数在调用点取用，行为与今天一致。
- 把 `now_utc` 改成在包装函数里先求值再传入（传值而非传函数）：同一秒内结果相同，但改变了时钟读取位置；本方案明确传函数，避免这种歧义。
- 直接执行 runner 时工作目录不是 `scripts/`：加载用 `Path(__file__)`，与工作目录无关。

## 实施位置与顺序

1. **计划审核**：本文件取得 `Plan conclusion: APPROVED`。
2. **本地执行代理**（按获批计划实施）：
   - 新增 `scripts/_stage3_render.py`：六个函数按目标修订行区间原样搬入，两个公开渲染器加关键字注入，文件头补所需导入。
   - `scripts/contact_state.py`：删除被搬走的块；按既有做法加载新模块；保留两个同名同签名入口与四个私有 helper 别名；两个调用点不动。
   - `tests/test_stage5_immutable.py`、`tests/test_stage5_dualtarget_contract.py`：复制 runner 的夹具同时复制 `_stage3_render.py`。
3. **测试准备与审核**：测试工程师按 `Test Engineer Rule.md` 准备测试资产（见同目录 `test-plan.md`）。
4. **正式执行**：测试计划获批后执行受影响测试并记录结果；未受影响的通过结果沿用。

## 修订记录

- 第 1 版：首次提交计划审核。

## 审核状态

计划第 1 版为当前唯一计划，结论 **`Plan conclusion: APPROVED`**（P1–P4 全 PASS；独立计划审核于 2026-10-18 给出）。后续审核以本文件、需求原文、`PROJECT_CONSENSUS.md` 与 `Plan Reviewer Rule.md` 为输入。
