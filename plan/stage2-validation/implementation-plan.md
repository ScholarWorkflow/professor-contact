# Stage 2 划分第五批：把校验报告与 refine 层抽成内部模块（执行计划）

## 版本、来源与状态

- 需求来源：负责人 2026-10-20 的指示（Stage 2 划分；“contact_state.py 应收敛为 CLI 分发与确有调用方依赖的兼容入口，每个 stage 主体逻辑拆为单独模块”）。
- Requirement revision: 第 1 版。Canonical Plan revision: 第 3 版（第 1 版审核意见、第 4 批边界调整与绑定位置修正已并入）。
- Target repository revision: 引用基线 `d5a4f751fb80de4819d4a1de3ee829db52cea6fc`；当前 `main` 已前进到 `0f89ebd`（#105，只改 Stage 5 的 `cmd_stage5_list_inputs` 与帮助文本；rebase 后 10139 之后的参考行号整体 -2，实现按函数名/AST 定位）。工作分支 `refactor-stage2-validation` 从该提交拉出。
- Relevant upstream/runtime revision: N/A。
- Proposed review status: **APPROVED**（`Plan conclusion: APPROVED`；2026-10-20 计划审核，第 3 版 P1–P4 全 PASS，无 blocker）。
- 唯一规范来源：本文件。

## 所属划分与边界

Stage 2 分 6 批。第 1 批（`_stage2_preflight.py`，PR #108）、第 2 批（`_stage2_resolve.py`，PR #109）已提交；本批是第 5 批，搬 **14 个函数 / 838 行**：

- 校验报告与 refine：`stage2_parse_report_location`、`stage2_validation_report`、`stage2_require_recorded_validation`、`stage2_pack_matches_facts`、`stage2_validation_material`、`stage2_pack_scope`、`stage2_refine_context`、`cmd_stage2_refine_plan`、`cmd_stage2_refine_finalize`、`cmd_stage2_record_validation`；
- later-paper 渲染/恢复 helper：`stage2_bound_render`、`stage2_merge_later_paper_source`、`stage2_rendered_later_papers`、`stage2_restore_pack_later_papers`（它们的消费者都在本批）。

第 4 批在 later-paper 组里只搬 `stage2_trusted_paper_title` 与 `stage2_require_later_paper_titles` 两个 finalize 运行期依赖（该批共 9 个函数）；本批通过 runner 别名使用它们，不重复搬。

## 正式需求与范围

- **R1 划分**：把本批 14 个函数原样移入新模块 `_stage2_validation.py`；`contact_state.py` 保留同名同签名入口。
- **R2 行为不变**：`stage2-record-validation`、`stage2-refine-plan`、`stage2-refine-finalize` 的 stdout、写入文件、失败原因码与退出码不变；校验报告的解析与渲染逐字节不变。
- **R3 依赖显式**：模块不 import runner、不改 `sys.path`、不注册 `sys.modules`；runner 名字全部显式注入。
- **R4 加载方式**：沿用既有内部模块做法（`Path(__file__).with_name` + `spec_from_file_location` + `module_from_spec` + `exec_module`）。
- **R5 兼容面**：14 个函数、CLI 三个子命令、`build_parser` 11645/11656/11854 与测试入口不改。

**非目标**：不改业务逻辑、指纹、schema、输出或排序；不搬两个上下文类与 facts/pack 渲染闭包（第 6 批）、resolve 层（第 2/3 批）、finalize 层（第 4 批）；不改测试、CLI、入口清单与 Nix 布局。

## 依据与关键事实

行号均指 `d5a4f75` 的 `scripts/contact_state.py`。

| 决定 | 关键事实 | 来源 |
| --- | --- | --- |
| 本批 14 个函数 | `stage2_pack_scope` 4218-4236(19)、`stage2_bound_render` 10139-10161(23)、`stage2_merge_later_paper_source` 10177-10189(13)、`stage2_rendered_later_papers` 10192-10228(37)、`stage2_restore_pack_later_papers` 10231-10242(12)、`stage2_parse_report_location` 10269-10296(28)、`stage2_validation_report` 10299-10573(275)、`stage2_require_recorded_validation` 10576-10623(48)、`stage2_pack_matches_facts` 10626-10728(103)、`stage2_validation_material` 10731-10759(29)、`stage2_refine_context` 10762-10769(8)、`cmd_stage2_refine_plan` 10772-10832(61)、`cmd_stage2_refine_finalize` 10835-10935(101)、`cmd_stage2_record_validation` 10938-11018(81)；合计 **838 行** | AST 实测 |
| 没有可搬常量 | 引用的 `MANAGED_BY`(189)、`INPUT_PACK`(221)、`ANALYSIS_MD`(226)、`QUOTE_INPUT_CHARS`(282)、`TRANSLATION_INPUT_CHARS`(283)、`PLACEHOLDER_RE`(296) 都有块外读取 | 全仓引用统计 |
| 38 个注入依赖 | 32 个 runner 函数/类：`Stage2Context`(1574)、`Stage2PackRefineContext`(1744)、`atomic_json`(57)、`emit`(60)、`fail`(65)、`soft_exit`(66)、`_stage3_normalized_absolute_path`(173)、`now_utc`(302)、`sha256_bytes`(306)、`sha256_text`(310)、`sha256_obj`(314)、`read_json_file`(331)、`truncate`(360)、`filename_component`(387)、`direction_machine_id`(398)、`pack_paper_index`(442)、`direction_papers`(447)、`load_input_pack`(590)、`pack_direction_relevant_keys`(1016)、`split_frontmatter`(1100)、`managed_conflict`(1117)、`managed_write`(1132)、`_canonical_directory`(2292)、`stage2_pack_state_fingerprint`(3722)、`stage2_pack_content_fingerprint`(3730)、`validate_narrative_entry`(4239)、`rendered_markdown_block_lines`(4360)、`render_positioning_block`(4371)、`render_analysis_md`(4573)、`stage2_require_paper_reference_titles`(4916，第 4 批别名)、`stage2_trusted_paper_title`(10164，第 4 批别名)、`stage2_require_later_paper_titles`(10245，第 4 批别名)；6 个常量：`MANAGED_BY`、`INPUT_PACK`、`ANALYSIS_MD`、`QUOTE_INPUT_CHARS`、`TRANSLATION_INPUT_CHARS`、`PLACEHOLDER_RE`；其中 `stage2_require_paper_reference_titles`／`stage2_trusted_paper_title`／`stage2_require_later_paper_titles` 是第 4 批的 9 个函数之一（合并后在 4722 的别名；未合并时在原位置，均早于 10267） | 自由名闭包 + 第 4 批计划 |
| 内部互调 19 处 | 14 个函数之间共 19 处调用，工厂闭包直接解析 | AST 统计 |
| 组外引用 | `build_parser` 11645/11656/11854 用 `p.set_defaults(func=...)` 引用三个命令；其余没有 | AST 统计 |
| 没有 import 期引用 | 14 个函数与 6 个常量没有出现在模块级语句、默认参数、装饰器或类体 | AST 检索 |
| 绑定位置 | 最晚依赖是 `stage2_require_later_paper_titles`（第 4 批，原 10245-10266；未合并时仍在 runner，合并后是 4722 的别名）；本批 build 必须在它的定义结束（10266）之后、`stage2_parse_report_location`（10269）之前，即 **10267**。只写“10242 之后”会放过 10243-10244，第 4 批未合并时必然导入期 `NameError` | 同上 |
| 跨批交互 | 第 4 批若先合并，其别名在 4722、本批 build 在 10267，成立；本批若先合并，第 4 批的 9 个定义仍在 runner，第 4 批 build 在 4722 也成立；两种顺序都不需要改对方的 build 实参 | 第 4 批计划 + AST |
| 加载与复制 | 两个夹具 `glob("_*.py")`（`test_stage5_immutable.py:220`、`test_stage5_dualtarget_contract.py:331`）；Nix 整树复制且 `entryNames` 不变（`nix/contact.nix:124-152`） | 仓库文件 |

## 方案

### 因果链

需求（校验/refine 层拆出）→ 现行机制（14 个函数分布在 4218-4236 与 10139-11018，依赖校验报告渲染、pack 指纹、写入 helper、两个上下文类与第 4 批的两个标题 helper）→ 变更点（原样移入 `_stage2_validation.py`，用一次 `build(**deps)` 在 10267 绑定；runner 保留同名入口）→ 行为变化（三个命令的输出、写入与失败路径不变；runner 少 838 行）→ 满足需求。

### 选定设计

- `_stage2_validation.py`：文件头 `from __future__ import annotations`、`import json`、`import re`、`from pathlib import Path`、`import types`；不定义常量；主体 `def build(*, ...38 个参数...)`（32 个 runner 函数/类 + 6 个常量），14 个函数原样嵌入（只增加缩进），返回 `types.SimpleNamespace`。
- runner：顶部按路径加载模块；在 `stage2_require_later_paper_titles` 定义结束（10266）之后、`stage2_parse_report_location`（10269）之前（即 10267）调用一次工厂并建立 14 个别名；删除原位 14 个定义；`build_parser` 调用点不改。
- 两个类留在 runner，以注入值使用；第 6 批搬类与渲染闭包时同步更新本批 `build` 实参。

**替代方向**：把 4 个 later-paper helper 留在第 4 批（它们的消费者都在本批，owner 应在本批）；逐函数关键字注入（19 处内部互调要补参）；模块 import runner（循环导入）；把两个类一起搬（第 6 批，方法体不能用闭包）。

### 冻结契约

- 14 个函数的名字、参数、默认值、返回结构、写入顺序与失败原因码不变；别名是同一函数对象。
- 6 个常量以同名参数注入，值不变；模块不定义常量。
- 错误通道只有 runner 一份；模块不 import `_contact_io`。
- CLI 三个子命令与入口清单不变。

## 影响

- **intended_change**：14 个函数移入新模块；runner 增加加载、一次绑定与 14 个别名。
- **preserved_behavior**：`stage2-record-validation`／`stage2-refine-plan`／`stage2-refine-finalize` 的 JSON、写入文件与顺序、失败路径；校验报告解析、阶段论文渲染与恢复；所有调用点、夹具与 Nix。
- **approved_behavior_change**：无。
- **prohibited_side_effect**：改逻辑/常量/输出/顺序；改测试；复制 helper 实现；新建第二错误通道；搬类、resolve、finalize；改 CLI/入口/Nix。
- **unresolved impact**：
  1. 函数元数据变化（`__module__`／`__qualname__`、`pickle`、`get_type_hints`）；仓内无消费者。
  1a. `build()` 在导入期捕获依赖；导入后 `mock.patch` runner 别名不会影响已搬函数及其互调（与第 1/2 批同一约束）；仓内未发现这种重绑。
  2. 第 6 批搬两个类与 `render_analysis_md` 时必须同步更新本批 build 实参（`build_direction_pack` 不在本批依赖内）。
  3. 第 4/5 批在 10266/10267 相邻删除/插入，合并时可能需要 rebase/冲突处理；不是语义前置。
  4. scripts 目录多一个内部模块。

## 关键安全条件与反例

1. 14 个函数的代码 AST 与搬移前逐字等价（只允许缩进与 docstring 续行缩进）。
2. 6 个常量值不变、只注入不复制。
3. runner 两条加载路径都能找到模块；工厂只调用一次且在 10266 之后、10269 之前（即 10267）。
4. 14 个名字与签名保持；`build_parser` 调用点不改。
5. 错误通道只有一份。
6. 三个命令的 stdout/写入不变。
7. 两个复制夹具自动带上新模块。

反例：工厂放在 10266 之前（尤其 10243-10244）→ 第 4 批未合并时导入期 `NameError`；缺关键字参数 → 工厂调用时 `TypeError`（导入期）；把 `PLACEHOLDER_RE` 复制进模块 → 与 runner 常量漂移；第 4 批未合并时本批仍能拿到 runner 里的原函数（别名注入）→ 成立；第 6 批搬类后忘记更新 `Stage2Context=`／`Stage2PackRefineContext=` 实参 → 闭包持有旧对象。

## 实施位置与顺序

1. 计划审核取得 `Plan conclusion: APPROVED`。
2. 新建模块；runner 顶部加载、10267 绑定与别名、删除原位 14 个定义；AST/常量/调用点对比。
3. 测试计划（`plan/stage2-validation/test-plan.md`）与执行记录。
4. M2 与合并审核另做。

## 修订记录

- 第 1 版：首次提交计划审核。
- 第 2 版：按第 4 批边界调整与第 4 批审核意见重写——本批改为 14 函数/838 行（接收 4 个 later-paper helper），注入依赖 32+6=38，补第 4 批别名交互与第 6 批渲染闭包影响。
- 第 3 版：按第二关复核把绑定位置统一为 `stage2_require_later_paper_titles` 定义结束（10266）之后、`stage2_parse_report_location`（10269）之前（即 10267），安全条件/选定设计/步骤/反例/修订记录同步；补 unresolved impact 的闭包捕获说明。

## 审核状态

- 计划审核：`Plan conclusion: APPROVED`（2026-10-20，第 3 版；P1–P4 全 PASS，`Required modifications: N/A`）。第 1/2/3 版的边界调整与绑定位置修正均已关闭。
- 测试计划：`plan/stage2-validation/test-plan.md` 第 1 版（待审核，随本批 PR 提交）。
- 测试执行：`plan/stage2-validation/test-execution-2026-10-20.md`（T0–T5 通过，A/B 78 条 `OK`、T4 10 个方法、T5 2 个方法）。

## 记录

- 对比证据放 `/tmp`；测试计划与执行记录在 `plan/stage2-validation/` 下。
- 2026-10-20 执行记录：被测代码提交 `76f107a`（父提交 `e973ffb`）；runner 10293 行 sha256 `e75593eb092d79e36dd68d18e849eac60c920caf0fcbd744a402ef7e3e8da9a3`，模块 924 行 sha256 `6e6e8c51857390f396f3fdbb850d10a674334e17b2c84e5da179ef26a89ac347`。
- 实施中 `origin/main` 从 `0f89ebd` 前进到 `e973ffb`（PR #108 合入第 1 批）；本批重放到新基准，14 个函数在两次提交间 AST 相同。
