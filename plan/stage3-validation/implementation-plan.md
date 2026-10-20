# Stage 3 划分第一批：校验与报告管线（执行计划）

## 版本、来源与状态

- Requirement revision: 第 1 版（2026-10-20 负责人要求：`contact_state.py` 收敛为 CLI 分发与确有调用方依赖的兼容入口；同一系列见 PR #95–#117）。
- Plan revision: 第 2 版。
- Proposed review status: 待审核。
- Target repository revision: 工作分支 `refactor-stage3-validation`，父提交为堆栈末位 `refactor-input-pack`（#117）的 head。基准一律用 `git rev-parse origin/refactor-input-pack` 动态取；当前值 `6ff8549`。
- 参考做法：`_stage3_render.py`、`_stage3_handoff.py`、`_contact_*`、`_stage2_*` 的“按路径加载 + 工厂闭包 + runner 同名别名”。

## 目标与验收条件

| 编号 | 目标 | 验收条件 |
| --- | --- | --- |
| R1 | 18 个 Stage 3 校验／报告管线定义离开 runner 顶层 | 18 个名字都不再在 `contact_state.py` 顶层定义；都出现在 `_stage3_validation.py` 的 `build()` 内；runner 有 18 个同名别名 |
| R2 | 搬移不改变逻辑 | 18 个定义体除缩进外逐字相同；自由名字全部来自 `build()` 的 36 个 keyword-only 参数、同批定义或模块 import |
| R3 | 依赖显式注入，模块不反向依赖 runner | `_stage3_validation.py` 不 `import contact_state`、不按路径加载 runner、不做动态导入、不碰 `sys.path`／`sys.modules` |
| R4 | 绑定点早于所有使用方 | 绑定块放在 `_load_stage3_handoff`（1475）之后、`cmd_stage3_plan`（1745）之前；`cmd_stage3_plan`／`cmd_stage3_finalize` 运行期经别名解析 |
| R5 | 其余行为不变 | 不改常量值、CLI 子命令、帮助文本、Nix 布局与测试文件；`contact_state.py --help` 与父提交逐字节相同 |
| R6 | 接缝可核对 | `git diff --ignore-blank-lines -U0` 只出现加载块、绑定块、18 个定义删除；**基中原位于搬移区间之外的两处空行块（3 行、6 行）在产物中保持原尺寸**；删除 18 个定义后合并出的两处空行块（24 行、20 行）收敛为 2 行；演练的 `git diff --ignore-blank-lines -U0` 为 8 个 hunk |

## 范围：18 个定义、824 行

| 定义 | 行区间 | 行数 |
| --- | --- | --- |
| `_stage3_bound_render` | 967–982 | 16 |
| `_stage3_candidates_entry` | 987–1023 | 37 |
| `stage3_validation_evidence` | 1028–1077 | 50 |
| `stage3_correction_scopes` | 1080–1114 | 35 |
| `stage3_repairable_correction_directions` | 1117–1132 | 16 |
| `carry_stage3_validator` | 1135–1160 | 26 |
| `stage3_current_result` | 1163–1172 | 10 |
| `_paper_refs` | 1181–1184 | 4 |
| `require_stage3_correction_invariants` | 1187–1231 | 45 |
| `_write_stage3_invocation` | 1290–1325 | 36 |
| `_read_stage3_invocation` | 1334–1385 | 52 |
| `_require_invocation_source` | 1388–1394 | 7 |
| `_stage3_handoff_directory` | 1400–1412 | 13 |
| `_load_stage3_handoff` | 1415–1475 | 61 |
| `cmd_stage3_prepare_validation` | 1478–1563 | 86 |
| `cmd_stage3_write_validation` | 1574–1663 | 90 |
| `cmd_stage3_save_validation` | 1666–1742 | 77 |
| `cmd_stage3_record_validation` | 5494–5656 | 163 |

合计 824 行。行号只用于核对当前基线，实施按“18 个 AST 定义”删除，落到 6 个外层分组（段内空行仍保留并参与合并，不是整段抹掉）：967–1172、1181–1231、1290–1325、1334–1475、1478–1742、5494–5656。区间内必须**保留**的内容：`_stage3_selected_scope_keys`（1234–1287，第二批）、三个常量 `STAGE3_IMMUTABLE_CANDIDATE_FIELDS`（1175–1176）、`STAGE3_REPAIRABLE_CANDIDATE_FIELDS`（1177–1178）、`STAGE3_INVOCATION_SOURCE_PARAMS`（1328–1331）——它们是绑定时要注入的名字，误删会让 `build()` 直接 `NameError`。

### 需要注入的 36 个名字

第 3 批 handoff 模块的别名（14 个）：`scope_key@170`、`_stage3_issue_scopes@171`、`_stage3_validation_files@172`、`_stage3_normalized_absolute_path@173`、`_stage3_complete_write_result@174`、`_require_stage3_handoff_round@176`、`_stage3_json_object_pairs@177`、`_stage3_json_reject_constant@178`、`_stage3_write_buffer@181`、`stage3_render_line_scopes@184`（`_stage3_render`）、`STAGE3_INVOCATION_VERSION@949`、`STAGE3_INVOCATION_FILE@950`、`STAGE3_HANDOFF_VERSION@956`、`STAGE3_HANDOFF_ROOT@957`。

其余常量与共享 helper（22 个）：`atomic_json@57`、`emit@60`、`fail@65`、`soft_exit@66`、`STAGE3_VALIDATION_MAX_ROUNDS@168`、`INPUT_PACK@318`、`CANDIDATE_STATE@319`、`CANDIDATES_MD@324`、`now_utc@452`、`sha256_bytes@453`、`sha256_text@454`、`require_professor_dir_under_program@461`、`split_frontmatter@484`、`load_input_pack@514`、`load_candidate_state@519`、`profile_fingerprint@843`、`STAGE3_HANDOFF_FILE@958`、`STAGE3_VALIDATOR_OUTPUT_FILE@959`、`STAGE3_VALIDATION_TARGET_FILE@960`、`STAGE3_IMMUTABLE_CANDIDATE_FIELDS@1175`、`STAGE3_REPAIRABLE_CANDIDATE_FIELDS@1177`、`STAGE3_INVOCATION_SOURCE_PARAMS@1328`。

最晚的注入名定义在 1328 行，早于绑定点（1476）。

### 为什么把 `_stage3_selected_scope_keys` 留到第二批

它 54 行，只被 `cmd_stage3_plan`／`cmd_stage3_finalize` 使用（都在第二批），并且依赖 `canonical_professor_dir`（3251–3261，被 `validate_stage4_selections`、`_stage4_professor_commit`、`cmd_stage4_finalize`、`cmd_stage4_migrate_local` 共用，属共享基础层）。真正理由是**本批没有它的消费方**，把它留在第二批与它的两个调用方同批搬走最自然；顺带也避免把 Stage 4 的共享件卷进来。

## 设计

新模块 `_stage3_validation.py`，一次 `build()`：36 个 keyword-only 参数、18 个成员；加载块锚点取 `SCHEMA = 1`（268）所在行；绑定块插在 `_load_stage3_handoff` 之后（`cmd_stage3_prepare_validation` 之前的位置）。

### 取舍

1. **一批搬完 21 个定义（1740 行）**：单批过大，评审成本高，且 `cmd_stage3_plan`／`cmd_stage3_finalize` 各 390 行、与校验管线耦合弱，拆开更清楚。
2. **按“命令 vs helper”拆**：会把 `stage3_validation_evidence` 等被三个命令共用的 helper 与调用方拆到两个模块，产生跨模块依赖。
3. **按“校验管线 vs plan/finalize 命令”拆（选中）**：本批只搬校验管线（含四个 validation 命令），第二批搬三个大命令。

## 实施步骤

1. 用 `/tmp/pc-stage2-tools/extract_batch_v4.py`（144 行，sha256 `f47586beece5641b6a3a4308a9d26c1b55bda6592fc04329bf867dd1ada90273`）加 spec `/tmp/pc-stage10/spec-b10.json` 生成模块与 probe runner：模块名 `_stage3_validation`、18 个函数名、`constants: []`、`load_anchor` = `SCHEMA = 1` 所在行、`bind_after_line` = `_load_stage3_handoff` 的最后一行、36 个参数名、模块 import（按 AST 实测，只保留真正用到的）：`from pathlib import Path`、`from typing import Any`、`import json`、`import os`、`import sys`、`import tempfile`、`import types`。`datetime`／`re` 在本批 18 个定义里 0 次引用；缺 `os`／`sys`／`tempfile` 会让 prepare/write/save-validation 一执行就 `NameError`（演练的初版 T4 没覆盖这三条命令，因此第一次没发现）。
2. 删除 18 个定义（按 AST 行区间）；把删除后合并出来的两处超大空行块（24 行、20 行）收敛为 2 行；**删除段外**的两处空行块（3 行、6 行）保持原尺寸不动。注意 961–966 那 6 行本身不在任何删除段内，它与相邻分隔合并成了 24 行块，所以按“删除段内”去找会漏。
3. 接缝核对：`git diff --ignore-blank-lines -U0` 只允许出现加载块、绑定块、定义删除；没有常量值、import、CLI、入口清单改动。空行用只读脚本比对“删除段外两处（3 行、6 行）原尺寸、删除段内三处（983–986、1024–1027、1564–1573）随定义消失、合并处（24 与 20）收敛为 2”。
4. 逐字核对：18 个定义的 AST（忽略 docstring）与基线相同；定义内注释用“基线片段 vs 模块内去 4 空格缩进片段”的文本比对确认。
5. 运行测试计划全部编号；提交实现与文档，推送分支，开 PR（base 为 `refactor-input-pack`）。

## 验证方式

- 结构／AST 等价：`/tmp/pc-stage2-tools/compare_stage2_batch_v2.py`（94 行，sha256 `1ba8c0f4…`）对 18 个名字做 T0–T3，预期 **98 条 `OK`**（T0 3、T1 37、T2 21、T3 37）。
- 行为：覆盖 record-validation、prepare/write/save-validation、handoff 凭据与渲染绑定的既有测试方法（见测试计划 T4）。
- 仓库既有 CI 照常执行，不作为本批必测项。

## 不纳入本批范围

| 未纳入项 | 原因 |
| --- | --- |
| `cmd_stage3_plan`（391）、`cmd_stage3_finalize`（387）、`cmd_stage3_rebuild_overview`（92）、`_stage3_selected_scope_keys`（54） | 第二批；后者依赖共享层的 `canonical_professor_dir` |
| Stage 4／Stage 5／迁移命令 | 后续批次 |
| 常量值、CLI、帮助文本、Nix 布局、测试文件 | 本批只做搬移 |

## 风险与反例

1. **绑定点早于 `cmd_stage3_plan`**：它直接使用 7 个本批名字（`_read_stage3_invocation`、`_require_invocation_source`、`_write_stage3_invocation`、`stage3_correction_scopes`、`stage3_current_result`、`stage3_repairable_correction_directions`、`stage3_validation_evidence`）；若绑定块放到 1745 之后，这些别名在命令执行时不存在。
2. **`cmd_stage3_record_validation` 在 5494**：它离主簇很远，但同批搬入、别名在 1476 处就已存在，运行期没有问题；删除后要在原位置收敛空行。
3. **空行块的两个集合**：删除段**内**的有三处——983–986（4 行）、1024–1027（4 行）、1564–1573（10 行）；961–966 那 6 行在删除段**外**，因为紧邻被删定义，会与相邻分隔合并成 24 行块。删除段**外**还有 2442–2444（3 行）与 5429–5434（6 行），必须原样保留。删除 18 个定义后合并出两个大块（24 与 20），都必须收敛为 2；只按“全部收敛为 2”会把段外那两处也改坏（第 9 批已踩过一次）。
4. **提取器版本**：本批用 v4 生成后再手工收敛两处合并出来的空行块。此前几批遇到过 v5／v6 的“删除处自动收敛空行”逻辑把文件末尾 `if __name__ == "__main__": sys.exit(main())` 一并吃掉的情况（表现为 `--help` 退出码 0 但无输出），本批未复现，但仍保留 `--help` 逐字节比对作兜底。
5. **docstring 缩进**：搬入 `build()` 后 docstring 续行加 4 空格；docstring 核对要读整行摘要，不能只看退出码。

## 实施前演练

按同一 spec 用 v4 生成并手工收敛后：模块 922 行、runner 5565 行；`--help` 与父提交逐字节相同；A/B 98 条 `OK`（T0 3、T1 37、T2 21、T3 37）；docstring `total=18 with_doc=16 multi=13 clean_equal=16 without_doc=2 missing=0 mismatched=0`；T4 10 个方法（9 个经 CLI 子进程，其中 5 个 handoff 方法覆盖 prepare／write／save／record-validation；1 个直接调用 `_stage3_bound_render`）、T5 2 个方法通过；runner 侧 8 个 hunk（加载块、六段定义删除、绑定块）。演练的初版 T4 只覆盖 record-validation，漏掉 prepare/write/save，导致模块缺 `os`／`sys`／`tempfile` 未被发现；换成新 T4 后立刻暴露并修正，这也写进了测试计划的已知限制说明。

## 修订记录

- 第 1 版：首次提交（含演练实测数据）。
- 第 2 版：按审核修正——① 范围由“967–1742 连续”改为“按 18 个 AST 定义删除、6 个删除段”，并列出必须保留的 `_stage3_selected_scope_keys` 与三个常量；② 模块 import 补 `os`／`sys`／`tempfile`、删 `datetime`／`re`（演练初版 T4 没覆盖 prepare/write/save，所以第一次没发现 `NameError`）；③ 空行事实改为“合并出 24 行与 20 行两块、演练 8 个 hunk”，风险 3 同步；④ 风险 1 换成 `cmd_stage3_plan` 直接使用的 7 个名字；⑤ `_stage3_selected_scope_keys` 的留批理由改成“本批没有消费方”，并更正 `canonical_professor_dir` 的行号与使用方；⑥ 风险 4 注明 v5／v6 的问题是历史经验、本批未复现。

## 审核状态

- 第 1 版：P1–P4 NEEDS_MODIFICATION（范围、import、T4 覆盖、空行归属）。
- 第 2 版：P1–P4 全 PASS，`Plan conclusion: APPROVED`（复核确认空行归属 24／20、961–966 在删除段外、段内三处为 983–986／1024–1027／1564–1573）。
