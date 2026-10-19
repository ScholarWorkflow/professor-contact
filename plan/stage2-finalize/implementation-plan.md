# Stage 2 划分第四批：把 finalize 层抽成内部模块（执行计划）

## 版本、来源与状态

- 需求来源：负责人 2026-10-20 的指示（Stage 2 划分；“contact_state.py 应收敛为 CLI 分发与确有调用方依赖的兼容入口，每个 stage 主体逻辑拆为单独模块”）。
- Requirement revision: 第 1 版。Canonical Plan revision: 第 2 版（第 1 版审核意见已并入，见修订记录）。
- Target repository revision: 交付基线 `e973ffb4571344157b3c43a151906a24f48c7e4e`（含第 1 批 #108）；引用基线 `d5a4f75`，中间 `main` 前进到 `0f89ebd`（#105，只改 Stage 5 的 `cmd_stage5_list_inputs` 与帮助文本；9 个函数 AST 与 `d5a4f75` 相同，4724-5546 与 4722 锚点不变，仅 8821 之后的参考行号整体 -2；`test_contact_state.py` 的直接调用在 `0f89ebd` 为 3109。实现按函数名/AST 定位）。工作分支 `refactor-stage2-finalize` 从该提交拉出；与第 1–3、5 批的行区间不重叠，可独立交付。
- Relevant upstream/runtime revision: N/A。
- Proposed review status: **APPROVED**（`Plan conclusion: APPROVED`；2026-10-20 计划审核，P1–P4 全 PASS，无 blocker）。
- 唯一规范来源：本文件。

## 所属划分与边界

Stage 2 分 6 批。第 1 批（`_stage2_preflight.py`，PR #108）与第 2 批（`_stage2_resolve.py`，PR #109）已提交；本批是第 4 批。

本批搬 **finalize 层 9 个函数**。其中 `stage2_trusted_paper_title`（10164-10174）与 `stage2_require_later_paper_titles`（10245-10266）在原划分里属第 5 批区间，但它们是 `stage2_require_paper_reference_titles`（4941）、`stage2_merge_later_paper_source`（10185，第 5 批）与 `cmd_stage2_finalize`（5426）的运行期依赖；若留给第 5 批，第 4 批的工厂就必须绑到 10245 之后，与第 5 批的搬移区间重叠。因此只把这 2 个 helper 移入本批；第 5 批保留 `stage2_bound_render`、`stage2_merge_later_paper_source`、`stage2_rendered_later_papers`、`stage2_restore_pack_later_papers` 这 4 个由校验报告/refine 消费的 helper（14 函数 / 838 行）。

| 批次 | 模块 | 内容 |
| --- | --- | --- |
| 1 / 2 / 3 | `_stage2_preflight.py` / `_stage2_resolve.py`（2、3 批共用） | 预检与身份 / resolve 计划 / resolve 提交 |
| 4（本批） | `_stage2_finalize.py` | finalize 预检漂移、渲染状态、引用标题校验、后续论文标题 helper、`stage2-finalize` 命令（9 函数 / 844 行） |
| 5 | `_stage2_validation.py` | 校验报告、refine、record-validation 及其 pack/validation/later-paper 渲染 helper（14 函数 / 838 行） |
| 6 | `_stage2_context.py` | 两个上下文类与 facts/pack 渲染闭包（含 `build_direction_pack`、`render_analysis_md`） |

## 正式需求与范围

- **R1 划分**：把本批 9 个函数原样移入新模块 `_stage2_finalize.py`；`contact_state.py` 保留同名同签名入口。
- **R2 行为不变**：`stage2-finalize` 的 stdout JSON、写入文件、失败原因码与退出码不变；预检漂移、成员重建、渲染状态、引用标题与后续论文标题处理逐字节不变。
- **R3 依赖显式**：模块不 import runner、不改 `sys.path`、不注册 `sys.modules`；runner 名字全部以显式参数注入，模块内不出现第二份实现。
- **R4 加载方式**：沿用既有内部模块做法（`Path(__file__).with_name` + `spec_from_file_location` + `module_from_spec` + `exec_module`）。
- **R5 兼容面**：9 个函数、常量、CLI 与现有调用点（`cmd_stage2_refine_plan` 10801、`cmd_stage2_refine_finalize` 10865/10899、`build_parser` 11636）不改；`test_contact_state.py:3068` 对 `contact_state.cmd_stage2_finalize` 的直接调用保持可用。

**非目标**：不改业务逻辑、指纹、schema、输出或排序；不搬 `Stage2Context`／`Stage2PackRefineContext`（第 6 批）、resolve 层（第 2/3 批）、校验报告与 refine（第 5 批）、facts/pack 渲染闭包（第 6 批）；不改测试、CLI、入口清单与 Nix 布局。

## 依据与关键事实

行号均指 `d5a4f75` 的 `scripts/contact_state.py`。

| 决定 | 关键事实 | 来源 |
| --- | --- | --- |
| 本批 9 个函数 | `stage2_preflight_plan_drift` 4724-4747(24)、`stage2_finalize_preflight_plan` 4750-4804(55)、`stage2_pack_requires_membership_rebuild` 4807-4829(23)、`stage2_old_pack_gap_statuses` 4832-4854(23)、`stage2_render_state` 4857-4913(57)、`stage2_require_paper_reference_titles` 4916-4945(30)、`cmd_stage2_finalize` 4948-5546(599)、`stage2_trusted_paper_title` 10164-10174(11)、`stage2_require_later_paper_titles` 10245-10266(22)；合计 **844 行** | AST 实测 |
| 两个 helper 是 finalize 的运行期依赖 | `stage2_require_paper_reference_titles` 4941 调 `stage2_trusted_paper_title`；`stage2_require_later_paper_titles` 10257 调它；`cmd_stage2_finalize` 5426 调 `stage2_require_later_paper_titles`；`render_analysis_md` 4578 也调 `stage2_require_later_paper_titles`（反向调用）；第 5 批的 `stage2_merge_later_paper_source` 10185 也调 `stage2_trusted_paper_title` | AST 调用图 |
| 没有可搬常量 | 引用的 `MANAGED_BY`(189)、`INPUT_PACK_SCHEMA`(196)、`DIRECTION_IDENTITY_VERSION`(205)、`INPUT_PACK_KIND`(208)、`RESOLVED_DIRECTION_SCHEMA`(220)、`ANALYSIS_MD`(226)、`STAGE2_RESOLUTION_SEMANTICS_VERSION`(269)、`PLACEHOLDER_RE`(296) 都有块外读取 | 全仓引用统计 |
| 38 个注入依赖 | 30 个 runner 函数/类：`Stage2Context`(1574)、`Stage2PackRefineContext`(1744)、`atomic_json`(57)、`emit`(60)、`fail`(65)、`soft_exit`(66)、`now_utc`(302)、`sha256_text`(310)、`sha256_obj`(314)、`read_json_file`(331)、`direction_machine_id`(398)、`pack_paper_index`(442)、`pack_direction_relevant_keys`(1016)、`split_frontmatter`(1100)、`managed_write`(1132)、`save_freshness_cache`(1496)、`_resolve_evidence`(2470)、`_current_resolve_fingerprint`(2581)、`_facts_preflight_proof`(2917)、`_sidecar_preflight_proof`(2936)、`stage2_target_path`(3353)、`read_stage2_target`(3358)、`read_stage1_professor_entry`(3385)、`stage2_preflight_cheap_inputs`(3478)、`stage2_preflight_metadata`(3644)、`stage2_pack_content_fingerprint`(3730)、`validate_freshness_results`(4112)、`validate_narrative`(4323)、`build_direction_pack`(4404)、`render_analysis_md`(4573)；8 个常量：`MANAGED_BY`、`INPUT_PACK_SCHEMA`、`DIRECTION_IDENTITY_VERSION`、`INPUT_PACK_KIND`、`RESOLVED_DIRECTION_SCHEMA`、`ANALYSIS_MD`、`STAGE2_RESOLUTION_SEMANTICS_VERSION`、`PLACEHOLDER_RE`；最晚依赖 `render_analysis_md`（4573-4721） | 自由名闭包 |
| 内部互调 10 处 | 9 个函数之间共 10 处调用，工厂闭包直接解析 | AST 统计 |
| 组外调用点 | `render_analysis_md` 4578 调 `stage2_require_later_paper_titles`（反向调用）；`cmd_stage2_refine_plan` 10801、`cmd_stage2_refine_finalize` 10865 调 `stage2_require_later_paper_titles`；`cmd_stage2_refine_finalize` 10899 调 `stage2_require_paper_reference_titles`；`stage2_merge_later_paper_source` 10185 调 `stage2_trusted_paper_title`（第 5 批函数调用本批 helper）；`build_parser` 11636 引用 `cmd_stage2_finalize`；测试 `test_contact_state.py:3068` 直接调用 `cmd_stage2_finalize` | AST 统计 + 测试检索 |
| 没有 import 期引用 | 9 个函数与 8 个常量没有出现在模块级语句、默认参数、装饰器或类体中；`render_analysis_md` 只在运行期调用 | AST 检索 |
| 绑定位置 | `render_analysis_md` 定义结束于 4721；工厂与别名插在 4721 之后、`stage2_preflight_plan_drift`（4724）之前（即 4722-4723）；别名必须先于任何 `render_analysis_md` 的运行期调用；导入期不得调用 `render_analysis_md` | 同上 |
| 第 5 批交互 | 第 5 批保留 4 个 later-paper helper，其 build 在 `stage2_parse_report_location` 之前（10267 附近）；本批别名在 4722，早于第 5 批 build；第 5 批需要的 `stage2_trusted_paper_title`／`stage2_require_later_paper_titles` 就是本批别名；两种合并顺序都成立 | 第 5 批计划 + AST |
| 第 6 批影响 | 第 6 批搬两个类与 `build_direction_pack`／`render_analysis_md` 时，必须同步更新本批 build 的 `Stage2Context=`／`Stage2PackRefineContext=` 以及 `build_direction_pack=`／`render_analysis_md=` 实参，并处理 4578 的反向调用 | 本批依赖清单 |
| 加载与复制 | 两个夹具用 `glob("_*.py")`（`test_stage5_immutable.py:220`、`test_stage5_dualtarget_contract.py:331`）；Nix 整树复制且 `entryNames` 不变（`nix/contact.nix:124-152`） | 仓库文件 |

## 方案

### 因果链

需求（finalize 层从 runner 拆出）→ 现行机制（9 个函数分布在 4724-5546 与 10164-10266，依赖上下文类、facts 预检证明、pack 渲染与写入 helper；另有一个反向调用：`render_analysis_md` 运行期调 `stage2_require_later_paper_titles`）→ 变更点（原样移入 `_stage2_finalize.py`，用一次 `build(**deps)` 在 4722 绑定 runner 的名字；runner 保留同名别名）→ 行为变化（finalize 输出、写入与失败路径不变；runner 少 844 行）→ 满足需求。

### 选定设计

- `_stage2_finalize.py`：文件头 `from __future__ import annotations`、`from pathlib import Path`、`import types`（本批函数不需要 `re`）；不定义常量；主体 `def build(*, ...38 个参数...)`（30 个 runner 函数/类 + 8 个常量），9 个函数原样嵌入（只增加缩进），返回 `types.SimpleNamespace`。
- runner：顶部按路径加载模块；在 `render_analysis_md` 结束（4721）之后、`stage2_preflight_plan_drift`（4724）之前调用一次工厂并建立 9 个别名；删除原位 9 个定义；其它调用点不改。
- 两个类留在 runner，以注入值使用；第 6 批搬类与渲染闭包时同步更新本批 `build` 实参。

**替代方向**：只搬 2 个 helper、其余 4 个留第 5 批（本计划采用的边界）；6 个一起搬（4 个 helper 的 owner 在第 5 批，搬进来没有依据，且扩大审核面）；逐函数关键字注入（10 处内部互调要补参）；模块 import runner（循环导入）。

### 冻结契约

- 9 个函数的名字、参数、默认值、返回结构、写入顺序与失败原因码不变；别名是同一函数对象。
- 8 个常量以同名参数注入，值不变；模块不定义常量。
- 错误通道只有 runner 一份；模块不 import `_contact_io`。
- CLI `stage2-finalize` 与入口清单不变。

## 影响

- **intended_change**：9 个函数移入新模块；runner 增加加载、一次绑定与 9 个别名。
- **preserved_behavior**：`stage2-finalize` 的 JSON、写入文件与顺序、失败路径；预检漂移、成员重建、渲染状态、引用标题与后续论文标题处理；`render_analysis_md` 的反向调用；所有调用点、夹具与 Nix。
- **approved_behavior_change**：无。
- **prohibited_side_effect**：改逻辑/常量/输出/顺序；改测试；复制 helper 实现；新建第二错误通道；搬类、resolve、校验/refine、facts/pack 渲染闭包；改 CLI/入口/Nix。
- **unresolved impact**：
  1. 函数元数据变化（`__module__`／`__qualname__`、`pickle`、`get_type_hints`）；仓内无消费者。
  2. 第 6 批搬两个类与 `build_direction_pack`／`render_analysis_md` 时必须同步更新本批 build 实参，并处理 4578 的反向调用。
  3. 第 4/5 批在 10266/10267 相邻删除/插入，合并时可能需要 rebase/冲突处理；不是语义前置。
  4. scripts 目录多一个内部模块。

## 关键安全条件与反例

1. 9 个函数的代码 AST 与搬移前逐字等价（只允许缩进与 docstring 续行缩进）。
2. 8 个常量值不变、只注入不复制。
3. runner 两条加载路径都能找到模块；工厂只调用一次且在 `render_analysis_md` 结束（4721）之后、4724 之前；别名先于任何 `render_analysis_md` 运行期调用。
4. 9 个名字与签名保持；所有调用点与测试直调不改。
5. 错误通道只有一份。
6. `stage2-finalize` 的 stdout/写入不变。
7. 两个复制夹具自动带上新模块。

反例：工厂放在 `render_analysis_md` 定义结束（4721）之前（如 4572/4720）→ 导入期 `NameError`；缺关键字参数 → 4722 工厂调用时 `TypeError`（导入期）；把 `PLACEHOLDER_RE` 复制进模块 → 与 runner 常量漂移；第 6 批搬类后忘记更新 `Stage2Context=`／`Stage2PackRefineContext=` 实参 → 闭包持有旧对象；假设导入期不会调用 `render_analysis_md` 却在别名建立前调用它 → `NameError`。

## 实施位置与顺序

1. 计划审核取得 `Plan conclusion: APPROVED`。
2. 新建模块；runner 顶部加载、4722 绑定与别名、删除原位 9 个定义；AST/常量/调用点对比。
3. 测试计划（`plan/stage2-finalize/test-plan.md`）与执行记录。
4. M2 与合并审核另做。

## 修订记录

- 第 1 版：首次提交计划审核。
- 第 2 版：并入 2026-10-20 计划审核的六条修改：① 把 6 个 later-paper helper 的归组改为“只搬 2 个 finalize 运行期依赖，其余 4 个留第 5 批”，本批 9 函数/844 行；② 组外调用点补 `render_analysis_md` 4578、测试直调 3068，注入依赖改为 30+8=38；③ 绑定锚点改为 `render_analysis_md` 结束（4721）之后、4724 之前，并加入“别名先于运行期调用、导入期不调用”的不变量；④ 反例改为导入期 `TypeError`，补两个类的注入点；⑤ 影响补第 6 批渲染闭包与 4578 反向调用、第 5 批 build 交互；⑥ 第 5 批描述改为“校验报告、refine、record-validation 及其 helper”。

## 审核状态

- 计划审核：`Plan conclusion: APPROVED`（2026-10-20，P1–P4 全 PASS）。第 1 版的 6 条修改与第 2 版的 2 条 P1 修正均已关闭；P2–P4 复用前轮 PASS。
- 测试计划：`plan/stage2-finalize/test-plan.md` 第 2 版（待测试计划审核）。
- 测试执行：`plan/stage2-finalize/test-execution-2026-10-20.md`（被测实现提交 `47f609d`，交付基线 `e973ffb`；A/B 53 条 OK、T4 10 项 OK、T5 2 项 OK）。

## 记录

- 交付基线：PR #108（第 1 批）合并后 rebase 到 `e973ffb4571344157b3c43a151906a24f48c7e4e`；本批加载块保持 `load_anchor=188`，9 个函数 AST 与 `d5a4f75` 相同。
- 测试计划与执行记录在 `plan/stage2-finalize/` 下；对比证据放仓库外 `/tmp/pc-stage4/`。
