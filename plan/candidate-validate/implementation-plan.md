# 候选与跨方向校验划分：候选结果校验（执行计划）

## 版本、来源与状态

- Requirement revision: 第 1 版（2026-10-20 负责人要求；同一系列见 PR #95–#124）。
- Plan revision: 第 2 版。
- Proposed review status: 待审核。
- Target repository revision: 工作分支 `refactor-shared-helpers`，父提交为堆栈末位 `refactor-stage5-helpers`（#124）的 head `8e47d10`。基准用 `git rev-parse origin/refactor-stage5-helpers` 动态取。
- 参考做法：`_stage5_email.py`、`_stage5_commands.py`、`_stage4_commands.py` 的“按路径加载 + 工厂闭包 + runner 同名别名”。

## 目标与验收条件

| 编号 | 目标 | 验收条件 |
| --- | --- | --- |
| R1 | 5 个候选校验定义离开 runner 顶层 | 5 个名字都不再在 `contact_state.py` 顶层定义；都出现在 `_candidate_validate.py` 的 `build()` 内；runner 有 5 个同名别名 |
| R2 | 搬移不改变逻辑 | 5 个定义体除缩进外逐字相同；非内建自由名字全部来自 `build()` 的 7 个 keyword-only 参数、同批定义或模块 import |
| R3 | 依赖显式注入，模块不反向依赖 runner | `_candidate_validate.py` 不 `import contact_state`、不按路径加载 runner、不做动态导入、不碰 `sys.path`／`sys.modules` |
| R4 | 绑定点合法 | 绑定块放在 `_direction_slices` 结束（912）之后、`_stage3_commands` 的 `build()`（1601）之前；该 build 消费本批 4 个成员（`validate_candidate_result`、`validate_cross_result`、`render_candidates_md`、`render_candidates_overview`），另接收注入依赖 `_direction_slices`，共 5 个名字；“唯一消费方”只对那 4 个成员成立 |
| R5 | 其余行为不变 | 不改常量值、CLI 子命令、帮助文本、Nix 布局与测试文件；`--help` 与父提交逐字节相同 |
| R6 | 接缝可核对 | `git diff --ignore-blank-lines -U0` 只出现加载块、绑定块、定义删除（4 个 hunk）；probe 里合并出的三处空行块（3／8／6 行）收敛为 2；父提交自带的 6 行块（@2031–2036）保持原尺寸 |

## 范围：5 个定义、286 行

| 定义 | 行区间 | 行数 |
| --- | --- | --- |
| `_validate_candidate_core` | 1071–1216 | 146 |
| `validate_candidate_result` | 1219–1295 | 77 |
| `validate_cross_result` | 1298–1349 | 52 |
| `render_candidates_md` | 1362–1367 | 6 |
| `render_candidates_overview` | 1370–1374 | 5 |

### 需要注入的 7 个名字

`_stage3_render@40`、`fail@65`、`CANDIDATES_MD@408`、`ANCHORABLE@420`、`now_utc@481`、`direction_machine_id@497`、`_direction_slices@890`（最晚）。

### 为什么这批没有依赖环

上一批（邮件）出现环，是因为模块的依赖要在它之后才定义。这一批的 7 个注入名全部在 913 行之前定义完成（最晚的 `_direction_slices` 是 890–912），而唯一消费方 `_stage3_commands` 的 `build()` 在 1601——绑定点（913）夹在中间，两边都满足。

## 设计

新模块 `_candidate_validate.py`，一次 `build()`：7 个 keyword-only 参数、5 个成员；加载块锚点取 `SCHEMA = 1`（352）；绑定块插在 `_direction_slices` 之后。

- 模块 import（按 AST 实测并补工厂需要）：`from pathlib import Path`、`from typing import Any`、`import types`；另有模板固定的 `from __future__ import annotations`。

## 实施步骤

0. 从干净基线开始：`git status` 确认只有本次改动。
1. 用 `/tmp/pc-stage2-tools/extract_batch_v4.py`（144 行，sha256 `f47586beece5641b6a3a4308a9d26c1b55bda6592fc04329bf867dd1ada90273`）加 spec `/tmp/pc-stage17/spec-b17.json`（由 `/tmp/pc-stage17/make-spec.py` 从 AST 自动推导：5 个函数名、7 个参数、`load_anchor`=352、`bind_after_line`=912）生成模块与 probe runner。
2. 把 probe 的 `_candidate_validate.py` 与 `contact_state.probe.py` 复制回 `scripts/`；把模板里的“Stage-2 helper module”改成“Candidate validation helper module”。
3. 删除 5 个定义（只删 AST 定义的行区间）；probe 里合并出的 3／8／6 三处空行块收敛为 2；父提交自带的 6 行块保持原尺寸。
4. 接缝核对：`git diff --ignore-blank-lines -U0` 为 4 个 hunk（加载块、两段定义删除、绑定块）；没有常量值、import、CLI、入口清单改动。
5. 逐字核对：5 个定义的 AST（忽略 docstring）与基线相同；docstring 整行核对（5 个里 3 个有、全多行）。
6. 运行测试计划全部编号；提交实现与文档，推送分支，开 PR（base 为 `refactor-stage5-helpers`）。

## 验证方式

- 结构／AST 等价：`compare_stage2_batch_v2.py`（94 行，sha256 `1ba8c0f49346b1fa78c34fbeec4d82cdab206ebef6cbf1b629769f9e5e4346b6`）对 5 个名字做 T0–T3，预期 **33 条 `OK`**（T0 3、T1 11、T2 8、T3 11）。
- 行为：候选校验路径的既有测试方法（见测试计划 T4）。
- 仓库既有 CI 照常执行，不作为本批必测项。

## 不纳入本批范围

| 未纳入项 | 原因 |
| --- | --- |
| `compile_email_entry`／`_selection_direction_ids`／`validate_papers_override`／`assemble_followup_draft` | 需先建共享 email core 并把 `_stage5_email` 改成从它注入，单独一批 |
| contact evidence、stage1、profile/direction、verify 链、legacy 迁移 helper | 后续批次（约 480 行） |
| 常量值、CLI、帮助文本、Nix 布局、测试文件 | 本批只做搬移 |

## 风险与反例

1. **绑定点夹在依赖与消费方之间**：7 个注入名最晚在 890，消费方 `_stage3_commands` 的 build 在 1601；绑定点放到 1601 之后会让该 build 取不到本批名字。
2. **空行**：probe 里合并出 3／8／6 三块，需全部收敛为 2；父提交自带的 6 行块必须原样保留（本批第一次操作时误收敛过，靠比对基线块位置发现）。
3. **docstring**：5 个里 3 个有（全多行）、2 个没有；核对要读整行摘要。

## 实施前演练

按自动推导的 spec 生成、改掉模板文案并收敛空行后：模块 325 行、runner 2334 行；`--help` 与父提交逐字节相同；A/B 33 条 `OK`；docstring `total=5 with_doc=3 multi=3 clean_equal=3 without_doc=2 missing=0 mismatched=0`；T4 10 个方法、T5 2 个方法通过；runner 侧 4 个 hunk、diff `+29 −296`。

## 修订记录

- 第 1 版：首次提交（含演练实测数据）。
- 第 2 版：按审核修正 R4 的消费名口径（4 个搬移成员 + 注入依赖 `_direction_slices`，共 5 个；“唯一消费方”只对 4 个成员成立），并把“7 个注入名全部在 890 行之前”改成“912 行之前（`_direction_slices` 890–912）”。

## 审核状态

- 第 1 版：P1 NEEDS_MODIFICATION（R4 的消费名数量与归属）。
- 第 2 版：待复核。
