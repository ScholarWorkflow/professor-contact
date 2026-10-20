# 邮件核心划分：邮箱条目编译（执行计划）

## 版本、来源与状态

- Requirement revision: 第 1 版（2026-10-20 负责人要求；同一系列见 PR #95–#125）。
- Plan revision: 第 2 版。
- Proposed review status: 待复核。
- Target repository revision: 工作分支 `refactor-shared-helpers` 之后的新分支 `refactor-email-core`，父提交为 `3ffdab0`（PR #125 的 head）。基准用 `git rev-parse origin/refactor-shared-helpers` 动态取。
- 参考做法：`_stage4_commands.py`、`_stage5_email.py`、`_candidate_validate.py` 的“按路径加载 + 工厂闭包 + runner 同名别名”。

## 目标与验收条件

| 编号 | 目标 | 验收条件 |
| --- | --- | --- |
| R1 | 3 个邮箱条目定义离开 runner 顶层 | 3 个名字都不再在 `contact_state.py` 顶层定义；都出现在 `_email_core.py` 的 `build()` 内；runner 有 3 个同名别名；别名顺序与工厂参数顺序沿用既定接缝，重排视为接口变化 |
| R2 | 搬移不改变逻辑 | 3 个定义体除缩进外逐字相同；非内建自由名字全部来自 `build()` 的 5 个 keyword-only 参数（顺序同名对应）、同批定义或模块 import |
| R3 | 依赖显式注入，模块不反向依赖 runner | `_email_core.py` 不 `import contact_state`、不按路径加载 runner、不做动态导入、不碰 `sys.path`／`sys.modules` |
| R4 | 解开 `email_source_hash` 的依赖环 | `email_source_hash` 从 `_stage5_email.py` 的 `build()` 移到 `_email_core.py` 的 `build()`；`_stage5_email.build` 的参数由 14 个变为 12 个（去掉 `EMAIL_SOURCE_HASH_FIELDS`、`sha256_obj`，**不新增参数**），该文件不再出现 `email_source_hash`；runner 的 `email_source_hash` 别名改为从 `_email_core` 取；`_stage4_commands.build` 的 3 个注入名不变 |
| R5 | 绑定点合法 | 绑定块放在 `EMAIL_SOURCE_HASH_FIELDS` 定义结束（1125）之后（调用在 1130）、`_stage4_commands` 的 `build()`（1227）之前；该 build 消费本批 3 个成员。`_stage5_email` 的 `build()`（1418）在其后，但不再接触本批任何名字 |
| R6 | 其余行为不变 | 不改常量值、CLI 子命令、帮助文本、Nix 布局与测试文件；`--help` 与父提交逐字节相同 |
| R7 | 接缝可核对 | `git diff --ignore-blank-lines -U0` 全树 7 个 hunk：`contact_state.py` 4 个（加载块、定义删除含绑定块、旧别名删除、`_stage5_email` 关键字删除），`_stage5_email.py` 3 个（签名、定义删除、返回命名空间项删除）；probe 里合并出的 6 行与 3 行空行块收敛为 2；父提交自带的 6 行块（当前 1584–1589）保持原尺寸 |

## 范围：3 个定义 199 行 + 1 个跨模块下移定义

| 定义 | 行区间（父提交） | 行数 |
| --- | --- | --- |
| `compile_email_entry` | 1116–1274 | 159 |
| `validate_papers_override` | 1277–1293 | 17 |
| `_selection_direction_ids` | 1296–1318 | 23 |
| `email_source_hash`（从 `_stage5_email.py` 下移） | 该文件 37–39 | 3 |

### 需要注入的 5 个名字

`fail@65`、`sha256_obj@496`、`direction_machine_id@509`、`direction_papers@513`、`EMAIL_SOURCE_HASH_FIELDS@1110`（最晚）。

### 为什么这批必须把 `email_source_hash` 一起下移

`compile_email_entry` 的末行调用 `email_source_hash(entry)` 计算 `source_hash`。上一批（邮件组装）已经遇到同一个环：`email_source_hash` 由 `_stage5_email.build()`（父提交 1595）产出，而本批模块的唯一消费方 `_stage4_commands.build()` 在父提交 1404——**消费方在生产者之前**。若只注入 `email_source_hash`，绑定点必须放到 1595 之后，`_stage4_commands` 就拿不到 `compile_email_entry`。因此把 `email_source_hash`（只依赖 `EMAIL_SOURCE_HASH_FIELDS` 和 `sha256_obj`）一起放进 `_email_core`，环就解开了。

**不需要再注入给 `_stage5_email`**：该文件删掉定义和返回命名空间项后，函数体内没有任何引用（当前 `grep -c email_source_hash _stage5_email.py` 为 0）。因此不新增参数，避免留下无消费方的接口。

## 设计

新模块 `_email_core.py`，一次 `build()`：5 个 keyword-only 参数、4 个成员；加载块锚点取 `SCHEMA = 1`（364）；绑定块插在父提交 1318 之后（实际落在 `EMAIL_SOURCE_HASH_FIELDS` 之后、`canonical_professor_dir` 之前）。

- 模块 import（按 AST 实测并补工厂需要）：`from pathlib import Path`、`from typing import Any`、`import types`；另有模板固定的 `from __future__ import annotations`。
- `_stage5_email.py` 的 `build()` 参数由 14 个变为 12 个；其返回的 `SimpleNamespace` 去掉 `email_source_hash`，该文件全文不再出现这个名字。
- `EMAIL_SOURCE_HASH_FIELDS` 留在 runner（schema 常量，仍由 `_email_core` 一个消费方使用）。

## 实施步骤

0. 从干净基线开始：`git status` 确认只有本次改动。
1. 用 `/tmp/pc-stage2-tools/extract_batch_v4.py`（144 行，sha256 `f47586beece5641b6a3a4308a9d26c1b55bda6592fc04329bf867dd1ada90273`）加 spec `/tmp/pc-stage18/spec-b19.json`（3 个函数名、5 个参数、`load_anchor`=364、`bind_after_line`=1318）生成模块与 probe runner。
2. 在 probe 的 `_email_core.build()` 里补 `email_source_hash` 定义并注册到返回的 `SimpleNamespace`；把模板里的“Stage-2 helper module”改成“Email core helper module”。
3. 把 probe 的 `_email_core.py` 与 `contact_state.probe.py` 复制回 `scripts/`；删除 3 个定义；probe 里合并出的 6 行与 3 行两处空行块收敛为 2；父提交自带的 6 行块保持原尺寸。
4. 改 `_stage5_email.py`：删 `email_source_hash` 定义、删 `EMAIL_SOURCE_HASH_FIELDS`／`sha256_obj` 两个参数（14→12）、从返回命名空间删该项；**不加任何新参数**。改 runner 的 `_stage5_email.build` 调用（删掉两个关键字、不新增关键字）与 `email_source_hash` 别名来源（改为 `_email_core`）。
5. 接缝核对：`git diff --ignore-blank-lines -U0` 全树 7 个 hunk（runner 4、`_stage5_email.py` 3）；没有常量值、CLI、入口清单改动。
6. 逐字核对：3 个定义的 AST（忽略 docstring）与基线相同；docstring 整行核对（3 个都有、2 个多行）；`email_source_hash` 定义体 AST 相同。
7. 运行测试计划全部编号；提交实现与文档，推送分支，开 PR（base 为 `refactor-shared-helpers`）。

## 验证方式

- 结构／AST 等价：`compare_stage2_batch_v2.py`（94 行，sha256 `1ba8c0f49346b1fa78c34fbeec4d82cdab206ebef6cbf1b629769f9e5e4346b6`）对 3 个名字做 T0–T3，预期 **23 条 `OK`**（T0 3、T1 7、T2 6、T3 7）。
- `email_source_hash` 专项：定义体 AST 相同；同一 `entry` 的哈希值相同（`15948fc9…`）；runner 别名就是模块命名空间里的函数（`is`）；签名相同。
- 行为：邮箱编译路径的既有测试方法（见测试计划 T4），并用插桩确认 4 个函数都被调用。
- 仓库既有 CI 照常执行，不作为本批必测项。

## 不纳入本批范围

| 未纳入项 | 原因 |
| --- | --- |
| `assemble_followup_draft` | 需要 `stage5_recipient_authority`（`_stage5_commands` 的成员，父提交 1673 才产出）；放到下一批单独处理 |
| contact evidence、stage1、profile/direction、verify 链、legacy 迁移 helper | 后续批次（约 480 行） |
| 常量值、CLI、帮助文本、Nix 布局、测试文件 | 本批只做搬移 |

## 风险与反例

1. **依赖环**：只搬 3 个定义而不下移 `email_source_hash`，绑定点与两个 build 的顺序无法同时满足（详见上一节）。
2. **多余接口**：若把 `email_source_hash` 再注入 `_stage5_email`，该参数在函数体内 0 次使用，传错值也不会被 T4／T5 发现；本版明确不注入。
3. **空行**：probe 里合并出 6／3 两处需收敛为 2；父提交自带的 6 行块（`_stage2_validation` 绑定点之前）必须原样保留，否则会被误判成多余空行。
4. **hunk 口径**：R7 的 4 个 hunk 只对 `contact_state.py` 成立；全树是 7 个，核对时必须限定路径。
5. **docstring**：3 个都有，其中 `compile_email_entry`、`_selection_direction_ids` 为多行；`validate_papers_override` 为单行。

## 实施前演练

按上述步骤生成并收敛空行后：模块 234 行、runner 2154 行（父提交 2334 行）、`_stage5_email.py` 499 行；`--help` 与父提交逐字节相同（sha256 `d622b7e6…`）；A/B 23 条 `OK`；docstring `total=3 with_doc=3 multi=2 clean_equal=3`；T4 7 个方法通过（插桩计数：`_selection_direction_ids` 21、`validate_papers_override` 17、`compile_email_entry` 8（7 次单方向 + 1 次跨方向组）、`email_source_hash` 8）；T5 1 个方法通过；普通 diff 与默认上下文的 `--ignore-blank-lines` 均为 `+26 −213`（`-U0` 下为 `+27 −214`）；hunk：runner 4、`_stage5_email.py` 3、全树 7。

## 修订记录

- 第 1 版：首次提交（含演练实测数据）。
- 第 2 版：按审核修正三处——R4／设计改为“14→12，不新增参数”，删除 `_stage5_email.build` 的无消费方参数与 runner 关键字；R5 改为“`_stage5_email` 不再接触本批名字”；R7／步骤 5 把 hunk 命令限定到 `contact_state.py` 并补 `_stage5_email.py` 的 3 个 hunk；数字更新为 runner 2154、`_stage5_email.py` 499、diff `+26 −213`。

## 审核状态

- 第 1 版：NEEDS_MODIFICATION（P1-1 参数计数、P1-2 无消费方参数、P1-3 hunk 口径）。
- 第 2 版：`Plan conclusion: APPROVED`（P1–P4 全 PASS）；非阻塞备注：`-U0` 的 stat 为 `+27 −214`、6 行块当前在 1584–1589。
