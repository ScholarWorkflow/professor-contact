# Stage 5 划分第二批：计划、终稿与概览命令（执行计划）

## 版本、来源与状态

- Requirement revision: 第 1 版（2026-10-20 负责人要求；同一系列见 PR #95–#120）。
- Plan revision: 第 3 版。
- Proposed review status: 待审核。
- Target repository revision: 工作分支 `refactor-stage5-commands`，父提交为堆栈末位 `refactor-stage5-input`（#120）的 head `ce46f36`。基准一律用 `git rev-parse origin/refactor-stage5-input` 动态取。
- 参考做法：`_stage5_input.py`、`_stage3_commands.py`、`_stage2_*`、`_contact_*` 的“按路径加载 + 工厂闭包 + runner 同名别名”。

## 目标与验收条件

| 编号 | 目标 | 验收条件 |
| --- | --- | --- |
| R1 | 5 个 Stage 5 命令定义离开 runner 顶层 | 5 个名字都不再在 `contact_state.py` 顶层定义；都出现在 `_stage5_commands.py` 的 `build()` 内；runner 有 5 个同名别名 |
| R2 | 搬移不改变逻辑 | 5 个定义体除缩进外逐字相同；非内建自由名字全部来自 `build()` 的 51 个 keyword-only 参数、同批定义或模块 import |
| R3 | 依赖显式注入，模块不反向依赖 runner | `_stage5_commands.py` 不 `import contact_state`、不按路径加载 runner、不做动态导入、不碰 `sys.path`／`sys.modules` |
| R4 | 绑定点合法 | 绑定块放在 `render_fact_check_card` 结束（3008）之后；最晚的注入名就是它（2977 起），`cmd_stage5_plan` 等命令只在 `main()` 运行时经别名取用 |
| R5 | 其余行为不变 | 不改常量值、CLI 子命令、帮助文本、Nix 布局与测试文件；`contact_state.py --help` 与父提交逐字节相同 |
| R6 | 接缝可核对 | `git diff --ignore-blank-lines -U0` 只出现加载块、绑定块、定义删除；probe（已含绑定块与别名）为 3679 行、三处合并空行块 4／4／9；把三处都收敛为 2 后减 11 行得最终 3668 行（相对 HEAD 净删 9 个空行，641−632）；父提交自带的两处（3 行 @1728–1730、6 行 @3464–3469）保持原尺寸 |

## 范围：5 个定义、632 行

| 定义 | 行区间 | 行数 |
| --- | --- | --- |
| `cmd_stage5_plan` | 2374–2563 | 190 |
| `stage5_recipient_authority` | 2657–2681 | 25 |
| `cmd_stage5_finalize` | 3011–3278 | 268 |
| `cmd_stage5_rebuild_overview` | 3281–3369 | 89 |
| `cmd_stage5_record_validation` | 3372–3431 | 60 |

合计 632 行，落在五段。

### 需要注入的 51 个名字

- 共享层与 Stage 2 别名（25 个）：`atomic_write@56`、`atomic_json@57`、`emit@60`、`fail@65`、`soft_exit@66`、`contact_evidence_decisions@128`、`resolve_contact_evidence@147`、`SCHEMA@304`、`MANAGED_BY@322`、`EMAIL_PACK@356`、`EMAIL_STATE@357`、`EMAIL_OVERVIEW@362`、`STAGE5_AUDIT_PROVENANCE@380`、`VERIFY_TIMESTAMP_FORMAT@401`、`now_utc@433`、`sha256_bytes@434`、`sha256_text@435`、`sha256_obj@436`、`read_json_file@440`、`require_professor_dir_under_program@442`、`truncate@443`、`rel_path@446`、`render_frontmatter@464`、`split_frontmatter@465`、`load_profile_text@833`。
- 第一批 Stage 5 别名（7 个）：`stage5_output_peers@2359`、`stage5_output_paths@2360`、`stage5_output_id@2361`、`stage5_mode@2363`、`stage5_pack_owner@2364`、`stage5_local_pack@2365`、`stage5_choices_by_id@2367`。
- 仍在 runner 的 helper（19 个）：`load_header_sources@2154`、`header_values@2172`、`subject_line@2196`、`current_source_fingerprints@2213`、`verify_state@2254`、`gap_job_block@2331`、`validate_email_raw@2566`、`require_user_choices@2645`、`require_followup_choices@2684`、`find_followup_template_path@2690`、`load_id_map@2700`、`humanized_paths@2723`、`assemble_draft@2808`、`assemble_followup_draft@2838`、`body_salutation_line@2873`、`render_checklist_table@2891`、`render_source_table@2931`、`render_followup_source_table@2963`、`render_fact_check_card@2977`。

最晚的是 `render_fact_check_card`（2977–3008），所以绑定点放在 3008 之后。模块内 5 个定义的排列顺序与源文件不同（extractor 按函数名列表输出），不构成契约——闭包按名字取用，与顺序无关。

## 设计

新模块 `_stage5_commands.py`，一次 `build()`：51 个 keyword-only 参数、5 个成员；加载块锚点取 `SCHEMA = 1`（304）所在行；绑定块插在 `render_fact_check_card` 之后。

- 模块 import（按 AST 实测并补工厂需要）：`from __future__ import annotations`（模板固定）、`from pathlib import Path`、`import json`、`import re`、`import types`。`types` 是 `build()` 返回 `SimpleNamespace` 所需，不在被搬定义里出现，容易被漏——演练时漏过一次，`--help` 直接 `NameError`。

### 取舍

1. **与第一批合并**：第一批已提交（#120），改动它会牵动那批的复核。
2. **按命令逐个拆**：`stage5_recipient_authority` 只 25 行且只被 finalize 用，单拆会产生跨模块依赖。
3. **5 个一起搬（选中）**：它们是同一层命令，共享 19 个仍在 runner 的 helper 与 7 个第一批别名（合计 25+7+19=51 个注入名），放一起注入一次最省。

## 实施步骤

0. 从干净基线开始：`git status` 确认只有本次改动；还原演练产物到 `ce46f36` 再开始。
1. 用 `/tmp/pc-stage2-tools/extract_batch_v4.py` 加 spec `/tmp/pc-stage13/spec-b13.json` 生成模块与 probe runner：模块名 `_stage5_commands`、5 个函数名、`constants: []`、`load_anchor` = `SCHEMA = 1`（304）、`bind_after_line` = 3008、51 个参数名、模块 import（`Path`、`json`、`re`、`types`）。
2. 删除 5 个定义（只删 AST 定义的 5 个行区间，段内空行保留并参与合并）；probe（已含绑定块与别名）里删除后会合并出 4／4／9 三处空行块，全部收敛为 2（3679−11=3668）；父提交自带的两处（3 行、6 行）保持原尺寸。
3. 接缝核对：`git diff --ignore-blank-lines -U0` 只允许出现加载块、绑定块、定义删除；没有常量值、import、CLI、入口清单改动；空行用只读脚本比对。
4. 逐字核对：5 个定义的 AST（忽略 docstring）与基线相同；docstring 整行核对；定义内注释用文本比对。
5. 把模板里的“Stage-2 helper module”改成“Stage-5 helper module”（模块 docstring 与 runner 加载块注释各一处）。
6. 运行测试计划全部编号；提交实现与文档，推送分支，开 PR（base 为 `refactor-stage5-input`）。

## 验证方式

- 结构／AST 等价：`compare_stage2_batch_v2.py`（94 行，sha256 `1ba8c0f4…`）对 5 个名字做 T0–T3，预期 **33 条 `OK`**（T0 3、T1 11、T2 8、T3 11）。
- 行为：`stage5-plan`／`stage5-finalize`／`stage5-rebuild-overview`／`stage5-record-validation` 的既有测试方法（见测试计划 T4）。
- 仓库既有 CI 照常执行，不作为本批必测项。

## 不纳入本批范围

| 未纳入项 | 原因 |
| --- | --- |
| `validate_email_raw`／`assemble_draft`／`render_*` 等 19 个 helper | 后续批次；本批按引用注入 |
| Stage 4、迁移、剩余共享 helper | 后续批次 |
| 常量值、CLI、帮助文本、Nix 布局、测试文件 | 本批只做搬移 |

## 风险与反例

1. **`types` 不在被搬定义里**：`build()` 的返回需要它，漏了会在 `--help` 时 `NameError`（演练已踩）。spec 的 import 必须包含 `types`。
2. **绑定点晚于 `render_fact_check_card`（2977–3008）**：放早会让 finalize 的注入名缺失；`cmd_stage5_plan` 在 2374 被删，运行期才取别名，不受位置影响。
3. **五段之间隔着 15 个定义**（注入名单里的 helper 是 19 个，两个数字口径不同）：删除按 AST 定义做，不会误删这些 helper；实施前用 AST 确认五段内只有这 5 个定义。
4. **空行**：probe（已含绑定块与别名）里合并出 4／4／9 三块，都收敛为 2（3679−11=3668）；父提交自带的 3 行与 6 行必须原样保留。
5. **docstring**：5 个里 2 个有（都多行）、3 个没有；核对要读整行摘要。

## 实施前演练

按同一 spec 用 v4 生成、改掉模板文案并手工收敛空行后：模块 716 行、runner 3668 行；`--help` 与父提交逐字节相同；A/B 33 条 `OK`；docstring `total=5 with_doc=2 multi=2 clean_equal=2 without_doc=3 missing=0 mismatched=0`；T4 10 个方法、T5 2 个方法通过；runner 侧 5 个 hunk。

## 修订记录

- 第 1 版：首次提交（含演练实测数据）。
- 第 2 版：按审核修正 §取舍旧计数、注入名单分组与空行的“+2”表述。
- 第 3 版：按审核修正计数与空行事实——注入名单分组 25／7／19（合计 51，名单不变），§取舍里的旧计数同步；“不纳入”表 helper 数改 19；风险 3 写明五段之间 15 个定义（注入 helper 19，两个口径）；空行写成“probe（已含绑定块与别名）4／4／9 → 全部收敛为 2，3679−11=3668，相对 HEAD 净删 9（641−632）”；补 `from __future__ import annotations` 与“模块内定义顺序不构成契约”。

## 审核状态

- 第 1 版：P1 NEEDS_MODIFICATION（分组计数、段间定义数、空行块）。
- 第 2 版：P1 NEEDS_MODIFICATION（§取舍旧计数、空行“+2”表述）。
- 第 3 版：P1–P4 全 PASS，`Plan conclusion: APPROVED`。
