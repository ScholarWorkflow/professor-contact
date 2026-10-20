# Stage 5 划分第三批：邮件组装与渲染（执行计划）

## 版本、来源与状态

- Requirement revision: 第 1 版（2026-10-20 负责人要求；同一系列见 PR #95–#123）。
- Plan revision: 第 2 版。
- Proposed review status: 待审核。
- Target repository revision: 工作分支 `refactor-stage5-helpers`，父提交为堆栈末位 `refactor-migrate`（#123）的 head `4a1138a`。基准一律用 `git rev-parse origin/refactor-migrate` 动态取。
- 参考做法：`_stage5_input.py`、`_stage5_commands.py`、`_stage4_commands.py` 的“按路径加载 + 工厂闭包 + runner 同名别名”。

## 目标与验收条件

| 编号 | 目标 | 验收条件 |
| --- | --- | --- |
| R1 | 22 个邮件组装／渲染定义离开 runner 顶层 | 22 个名字都不再在 `contact_state.py` 顶层定义；都出现在 `_stage5_email.py` 的 `build()` 内；runner 有 22 个同名别名 |
| R2 | 搬移不改变逻辑 | 22 个定义体除缩进外逐字相同；非内建自由名字全部来自 `build()` 的 14 个 keyword-only 参数、同批定义或模块 import |
| R3 | 依赖显式注入，模块不反向依赖 runner | `_stage5_email.py` 不 `import contact_state`、不按路径加载 runner、不做动态导入、不碰 `sys.path`／`sys.modules` |
| R4 | 绑定点合法 | 绑定块放在 `DEFAULT_ALMA_MATER`（2011）之后、`_stage5_commands` 的 `build()` 之前；后者用本批 22 个中的 **16 个**名字（另有一个 `assemble_followup_draft` 属下批，不属于本批） |
| R5 | 其余行为不变 | 不改常量值、CLI 子命令、帮助文本、Nix 布局与测试文件；`contact_state.py --help` 与父提交逐字节相同 |
| R6 | 接缝可核对 | `git diff --ignore-blank-lines -U0` 只出现加载块、绑定块、定义删除；probe 里合并出的五处空行块（4／16／4／16／12 行）收敛为 2；父提交自带的 6 行块（@2443–2448）保持原尺寸 |

## 范围：22 个定义、424 行

| 定义 | 行区间 | 行数 |
| --- | --- | --- |
| `email_source_hash` | 1371–1373 | 3 |
| `find_boshu_analysis` | 1706–1711 | 6 |
| `load_header_sources` | 1714–1729 | 16 |
| `header_values` | 1732–1753 | 22 |
| `subject_line` | 1756–1758 | 3 |
| `compact_name` | 1761–1762 | 2 |
| `email_item_is_evidence_seeded` | 1765–1770 | 6 |
| `current_source_fingerprints` | 1773–1788 | 16 |
| `validate_email_raw` | 1934–2005 | 72 |
| `require_user_choices` | 2013–2022 | 10 |
| `require_followup_choices` | 2025–2028 | 4 |
| `find_followup_template_path` | 2031–2038 | 8 |
| `load_id_map` | 2041–2061 | 21 |
| `humanized_paths` | 2064–2096 | 33 |
| `email_template_body` | 2099–2146 | 48 |
| `assemble_draft` | 2149–2176 | 28 |
| `body_salutation_line` | 2214–2229 | 16 |
| `render_checklist_table` | 2232–2260 | 29 |
| `cell_source` | 2263–2269 | 7 |
| `render_source_table` | 2272–2301 | 30 |
| `render_followup_source_table` | 2304–2315 | 12 |
| `render_fact_check_card` | 2318–2349 | 32 |

合计 424 行，分布在 1371–2349 的多个不连续区间。

### 需要注入的 14 个名字

`EMAIL_SOURCE_HASH_FIELDS@1365`、`sha256_obj@472`、`read_json_file@476`、`BATCH_RE@439`、`CLOSING_RE@438`、`INTEREST_HARD_CAP@434`、`INTEREST_SOFT_CAP@435`、`fail@65`、`stage5_mode@1923`、`stage5_output_id@1921`、`DEFAULT_ALMA_MATER@2011`、`EMAIL_PACK@392`、`now_utc@469`、`rel_path@482`。

最晚的是 `DEFAULT_ALMA_MATER`（2011），所以绑定点放在它之后。

### 为什么本批不含 `compile_email_entry`、`_selection_direction_ids`、`validate_papers_override`、`assemble_followup_draft`

这四个被更早的 `build()` 消费：

- `_stage4_commands` 的 `build()`（1664）需要 `compile_email_entry`、`_selection_direction_ids`、`validate_papers_override`；
- `_stage5_commands` 的 `build()`（2352）需要 `assemble_followup_draft`（它用 `stage5_recipient_authority`，而那个别名要等 `_stage5_commands` 建好才有）。

把它们一起搬会形成“本模块要等后面的别名、后面的 build 又要等本模块”的环。本批先搬不依赖这些的 22 个，其余四个留到下一批（届时它们的依赖已经就绪）。

## 设计

新模块 `_stage5_email.py`，一次 `build()`：14 个 keyword-only 参数、22 个成员；加载块锚点取 `SCHEMA = 1`（340）所在行；绑定块插在 `DEFAULT_ALMA_MATER` 之后、`_stage5_commands` 的 `build()` 之前。

- 模块 import（按 AST 实测并补工厂需要）：`from pathlib import Path`、`from typing import Any`、`import re`、`import unicodedata`、`import types`；另有模板固定的 `from __future__ import annotations`。
- 模块内定义顺序由 spec 的函数名列表决定；闭包按名字取用，顺序不构成契约。

### 取舍

1. **一次搬完 26 个（含被更早 build 消费的 4 个）**：会形成依赖环（见上），不可行。
2. **把它们搬到共享层再注入**：`compile_email_entry` 等确实是跨 stage 的，但那要改动已合并的 `_stage4_commands` 的注入来源，超出本批范围。
3. **先搬 22 个（选中）**：不触碰现有 build 的依赖来源，剩余 4 个留给下一批。

## 实施步骤

0. 从干净基线开始：`git status` 确认只有本次改动；还原演练产物到 `4a1138a` 再开始。
1. 用 `/tmp/pc-stage2-tools/extract_batch_v4.py`（144 行，sha256 `f47586beece5641b6a3a4308a9d26c1b55bda6592fc04329bf867dd1ada90273`）加 spec `/tmp/pc-stage16/spec-b16.json` 生成模块与 probe runner：模块名 `_stage5_email`、22 个函数名、`constants: []`、`load_anchor` = `SCHEMA = 1`（340）、`bind_after_line` = 2011、14 个参数名、模块 import（`Path`、`Any`、`re`、`unicodedata`、`types`）。spec 可由脚本按函数名列表与自由名自动推导（本批的 `/tmp/pc-stage16/make-spec.py` 即如此），`/tmp` 清理后可按本文的名单与锚点重建。两个工具脚本（`extract_batch_v4.py` 144 行 / `f47586beece5641b6a3a4308a9d26c1b55bda6592fc04329bf867dd1ada90273`、`compare_stage2_batch_v2.py` 94 行 / `1ba8c0f49346b1fa78c34fbeec4d82cdab206ebef6cbf1b629769f9e5e4346b6`）目前只在 `/tmp/pc-stage2-tools/`，若被清理需按“生成模块 + 改加载/绑定块”的步骤手工重做，或先备份该目录。
2. 删除 22 个定义（只删 AST 定义的行区间，段内空行保留并参与合并）；probe 里合并出的五处空行块（4／16／4／16／12）收敛为 2；父提交自带的 6 行块保持原尺寸。
3. 接缝核对：`git diff --ignore-blank-lines -U0` 只允许出现加载块、绑定块、定义删除；没有常量值、import、CLI、入口清单改动。注意 22 个别名可能与相邻删除区合并成一个替换 hunk（drill 实际是 7 个 hunk），这是预期形态，不算常量改动。
4. 逐字核对：22 个定义的 AST（忽略 docstring）与基线相同；docstring 整行核对（22 个里 5 个有、2 个多行）；定义内注释用文本比对——本批只有 `load_id_map` 含注释（2047–2049 三行），重点核这一处，其余 21 个没有注释。
5. 把模板里的“Stage-2 helper module”改成“Stage-5 email helper module”。
6. 运行测试计划全部编号；提交实现与文档，推送分支，开 PR（base 为 `refactor-migrate`）。

## 验证方式

- 结构／AST 等价：`compare_stage2_batch_v2.py`（94 行，sha256 `1ba8c0f4…`）对 22 个名字做 T0–T3，预期 **118 条 `OK`**（T0 3、T1 45、T2 25、T3 45）。
- 行为：`stage5-plan`／`stage5-finalize` 路径的既有测试方法（见测试计划 T4）。
- 仓库既有 CI 照常执行，不作为本批必测项。

## 不纳入本批范围

| 未纳入项 | 原因 |
| --- | --- |
| `compile_email_entry`／`_selection_direction_ids`／`validate_papers_override`／`assemble_followup_draft` | 被更早的 build 消费，一起搬会形成依赖环；下一批处理 |
| 候选校验（`validate_candidate_result` 等）、`verify_state`、contact evidence、stage1 读取、`read_legacy_index`／`classify_direction`／`apply_ready_entry` | 后续批次 |
| 常量值、CLI、帮助文本、Nix 布局、测试文件 | 本批只做搬移 |

## 风险与反例

1. **依赖环**：本批排除的 4 个定义被 1664／2352 的 `build()` 消费；若把它们一起搬，导入期就会 `NameError`。演练已验证：含 `compile_email_entry` 的版本在 1497 行报错。
2. **绑定点位置**：必须在 `_stage5_commands` 的 `build()`（2352）之前建立 22 个别名，而 `stage5_output_id`／`stage5_mode` 两个别名在 1921／1923 已就绪，`DEFAULT_ALMA_MATER` 在 2011——绑定点取 2011 之后即可同时满足两侧。
3. **空行**：probe 里合并出 4／16／4／16／12 五块，需全部收敛为 2；父提交自带的 6 行块必须原样保留。
4. **docstring**：22 个里 5 个有（2 个多行）、17 个没有；核对要读整行摘要。
5. **`compile_email_entry` 暂留 runner**：它在下一批搬走前，Stage 4 的 `build()` 仍从 runner 取它，行为不变。

## 实施前演练

按自动推导的 spec 生成、改掉模板文案并手工收敛空行后：模块 506 行、runner 2601 行；`--help` 与父提交逐字节相同；A/B 118 条 `OK`；docstring `total=22 with_doc=5 multi=2 clean_equal=5 without_doc=17 missing=0 mismatched=0`；T4 10 个方法、T5 2 个方法通过；runner 侧 7 个 hunk、diff `+52 −464`。

## 修订记录

- 第 1 版：首次提交（含演练实测数据）。
- 第 2 版：按审核修正——R4 的“17 个名字”改为“22 个中的 16 个”（第 17 个 `assemble_followup_draft` 属下批）；步骤 4 点名 `load_id_map` 的 2047–2049 三行注释；步骤 3 注明别名块可能表现为替换 hunk；步骤 1 补两个工具脚本的路径与哈希。

## 审核状态

- 第 1 版：P1 NEEDS_MODIFICATION（R4 的 17 与实际 16 不符）。
- 第 2 版：待复核。
