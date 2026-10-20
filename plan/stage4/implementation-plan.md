# Stage 4 划分：最终写入与迁移（执行计划）

## 版本、来源与状态

- Requirement revision: 第 1 版（2026-10-20 负责人要求；同一系列见 PR #95–#121）。
- Plan revision: 第 2 版。
- Proposed review status: 待审核。
- Target repository revision: 工作分支 `refactor-stage4`，父提交为堆栈末位 `refactor-stage5-commands`（#121）的 head `8c4b363`。基准一律用 `git rev-parse origin/refactor-stage5-commands` 动态取。
- 参考做法：`_stage5_commands.py`、`_stage3_commands.py`、`_stage2_*`、`_contact_*` 的“按路径加载 + 工厂闭包 + runner 同名别名”。

## 目标与验收条件

| 编号 | 目标 | 验收条件 |
| --- | --- | --- |
| R1 | 10 个 Stage 4 定义离开 runner 顶层 | 10 个名字都不再在 `contact_state.py` 顶层定义；都出现在 `_stage4_commands.py` 的 `build()` 内；runner 有 10 个同名别名 |
| R2 | 搬移不改变逻辑 | 10 个定义体除缩进外逐字相同；非内建自由名字全部来自 `build()` 的 27 个 keyword-only 参数、同批定义或模块 import |
| R3 | 依赖显式注入，模块不反向依赖 runner | `_stage4_commands.py` 不 `import contact_state`、不按路径加载 runner、不做动态导入、不碰 `sys.path`／`sys.modules` |
| R4 | 绑定点合法 | 绑定块放在 `cmd_stage4_migrate_local` 结束（2155）之后；27 个注入名里最晚的是常量 `STAGE4_MIGRATION_COMMITTED`（2077），早于绑定点 |
| R5 | 其余行为不变 | 不改常量值、CLI 子命令、帮助文本、Nix 布局与测试文件；`contact_state.py --help` 与父提交逐字节相同 |
| R6 | 接缝可核对 | `git diff --ignore-blank-lines -U0` 只出现加载块、绑定块、定义删除；probe 里合并出的空行块（4／6／13／4 行，以及别名块后的 3 行）全部收敛为 2；父提交自带的 3 行（@1740–1742）随 `stage4_professor_row` 删除并入 13 行块、没有单独保留，父提交的 6 行（@2895–2900）保持原尺寸；`STAGE4_MIGRATION_COMMITTED` 因中间定义删除从 2077 重排到 1647，内容未变；在 5 个 hunk 里它作为未变上下文出现，前后分别是定义删除与绑定块新增，属预期 |

## 范围：10 个定义、499 行

| 定义 | 行区间 | 行数 |
| --- | --- | --- |
| `_stage4_cross_group` | 1341–1361 | 21 |
| `validate_stage4_selections` | 1580–1656 | 77 |
| `stage4_local_pair_paths` | 1659–1661 | 3 |
| `stage4_professor_row` | 1743–1749 | 7 |
| `_stage4_failure_row` | 1752–1764 | 13 |
| `_stage4_professor_commit` | 1767–2019 | 253 |
| `stage4_professor_transaction` | 2022–2039 | 18 |
| `cmd_stage4_finalize` | 2042–2074 | 33 |
| `_stage4_migration_result` | 2080–2093 | 14 |
| `cmd_stage4_migrate_local` | 2096–2155 | 60 |

合计 499 行，分两段（1341–1361 与 1580–2155）。

### 需要注入的 27 个名字

- 共享层与早期批次别名（21 个）：`atomic_json_many@58`、`emit@60`、`ProfessorBusinessFailure@61`、`professor_business_channel@63`、`fail@65`、`soft_exit@66`、`contact_evidence_snapshot@106`、`load_contact_evidence@135`、`MANAGED_BY@334`、`STAGE4_LOCAL_SCHEMA@349`、`DIRECTION_IDENTITY_VERSION@350`、`SELECTION_KIND@355`、`EMAIL_PACK_KIND@356`、`EMAIL_PACK@368`、`SELECTION_FILE@375`、`now_utc@445`、`read_json_file@452`、`professor_dir_containment_error@453`、`direction_machine_id@461`、`load_input_pack@507`、`load_candidate_state@512`。
- 仍在 runner 的 helper（6 个）：`profile_fingerprint@836`、`compile_email_entry@1375`、`validate_papers_override@1536`、`_selection_direction_ids@1555`、`canonical_professor_dir@1664`、`STAGE4_MIGRATION_COMMITTED@2077`（常量）。

最晚的是常量 `STAGE4_MIGRATION_COMMITTED`（2077），在绑定点（2156）之前。

## 设计

新模块 `_stage4_commands.py`，一次 `build()`：27 个 keyword-only 参数、10 个成员；加载块锚点取 `SCHEMA = 1`（316）所在行；绑定块插在 `cmd_stage4_migrate_local` 之后。

- 模块 import（按 AST 实测并补工厂需要）：`from pathlib import Path`、`from typing import Any`、`import sys`、`import types`（`json` 在 10 个定义里没有引用，已从清单去掉）；另有模板固定的 `from __future__ import annotations`。
- 模块内 10 个定义的排列顺序与源文件一致；闭包按名字取用，顺序不构成契约。

### 取舍

1. **把 `canonical_professor_dir` 一起搬**：它是 Stage 3 与 Stage 4 共用的共享 helper（Stage 3 模块已把它作为注入参数），搬进 Stage 4 模块会破坏归属，本批按引用注入。
2. **只搬两条命令（`cmd_stage4_finalize`／`cmd_stage4_migrate_local`）**：`_stage4_professor_commit`（253 行）与 `validate_stage4_selections`（77 行）是它们的主体逻辑，留下等于没拆。
3. **10 个一起搬（选中）**：它们是同一条写入链（校验 → 事务 → 提交 → 结果行 → 迁移），共享同一批注入名。

## 实施步骤

0. 从干净基线开始：`git status` 确认只有本次改动；还原演练产物到 `8c4b363` 再开始。
1. 用 `/tmp/pc-stage2-tools/extract_batch_v4.py`（`/tmp` 清理后可用本文的 10 个函数名、27 个参数名与锚点（`SCHEMA = 1` @316、`bind_after_line`=2155）重建 spec）（144 行，sha256 `f47586be…`）加 spec `/tmp/pc-stage14/spec-b14.json` 生成模块与 probe runner：模块名 `_stage4_commands`、10 个函数名、`constants: []`、`load_anchor` = `SCHEMA = 1`（316）、`bind_after_line` = 2155、27 个参数名、模块 import（`Path`、`Any`、`sys`、`types`）。
2. 删除 10 个定义（只删 AST 定义的 10 个行区间，段内空行保留并参与合并；第二段里 `canonical_professor_dir`、Stage 3 的 build/别名块与常量 2077 都要保留）；probe 里合并出的空行块（4／6／13／4）与别名块后的 3 行全部收敛为 2；父提交的 6 行块保持原尺寸，父提交的 3 行块（@1740–1742）已并入 13 行块、随之一并收敛。
3. 接缝核对：`git diff --ignore-blank-lines -U0` 只允许出现加载块、绑定块、定义删除；没有常量值、import、CLI、入口清单改动；空行用只读脚本比对。
4. 逐字核对：10 个定义的 AST（忽略 docstring）与基线相同；docstring 整行核对；定义内注释用文本比对。
5. 把模板里的“Stage-2 helper module”改成“Stage-4 helper module”（模块 docstring 与 runner 加载块注释各一处）。
6. 运行测试计划全部编号；提交实现与文档，推送分支，开 PR（base 为 `refactor-stage5-commands`）。

## 验证方式

- 结构／AST 等价：`compare_stage2_batch_v2.py`（94 行，sha256 `1ba8c0f4…`）对 10 个名字做 T0–T3，预期 **58 条 `OK`**（T0 3、T1 21、T2 13、T3 21）。
- 行为：`stage4-finalize`／`stage4-migrate-local` 的既有测试方法（见测试计划 T4）。
- 仓库既有 CI 照常执行，不作为本批必测项。

## 不纳入本批范围

| 未纳入项 | 原因 |
| --- | --- |
| `canonical_professor_dir`／`compile_email_entry` 等 6 个 helper | 本批 10 个定义之外，按引用注入（`canonical_professor_dir`／`profile_fingerprint` 是跨 stage 共享，其余只被 Stage 4 使用） |
| Stage 5 的 17 个组装/渲染 helper、迁移命令的其余部分 | 后续批次 |
| 常量值、CLI、帮助文本、Nix 布局、测试文件 | 本批只做搬移 |

## 风险与反例

1. **两段相隔较远**（1341–1361 与 1580–2155）：按 AST 定义删除即可，不会误删中间的 `compile_email_entry` 等 helper；第二段内部还有必须保留的 `canonical_professor_dir`、Stage 3 的 build/别名块与常量 `STAGE4_MIGRATION_COMMITTED`（2077），删除时只按 10 个 AST 名字区间动手。
2. **绑定点必须晚于 `STAGE4_MIGRATION_COMMITTED`（2077）**：放早会让 `cmd_stage4_migrate_local` 的闭包参数缺失。
3. **空行**：probe 里合并出 4／6／13／4 四块、别名块后还有一块 3 行，全部收敛为 2；父提交的 6 行块（@2895–2900）必须原样保留，而 3 行块（@1740–1742）已并入 13 行块、不单独保留——按“尺寸”核对时不要把别名块后的 3 行误当成它。
4. **docstring**：10 个里 9 个有（6 个多行）、1 个没有；核对要读整行摘要。
5. **`sys` 与 `types`**：`sys` 在搬移的定义里直接使用（AST 可测），`types` 是 `build()` 返回 `SimpleNamespace` 所需（AST 测不到）——两者都要显式写进 spec，第 13 批已因漏 `types` 返工过一次。

## 实施前演练

按同一 spec 用 v4 生成、改掉模板文案并手工收敛空行后：模块 569 行、runner 3204 行；`--help` 与父提交逐字节相同；A/B 58 条 `OK`；docstring `total=10 with_doc=9 multi=6 clean_equal=9 without_doc=1 missing=0 mismatched=0`；T4 10 个方法、T5 2 个方法通过；runner 侧 5 个 hunk、diff `+53 −517`（其中 570→569 是去掉未使用的 `json`，3205→3204 与 hunk 数变化来自别名块后那块 3 行空行收敛为 2）。

## 修订记录

- 第 1 版：首次提交（含演练实测数据）。
- 第 2 版：按审核修正空行事实——13 行块（含 1740–1742 的 3 行）与别名块后的 3 行都收敛为 2，只有 2895–2900 的 6 行保留；补第二段保留项与 `STAGE4_MIGRATION_COMMITTED` 的重排说明；取舍 2 改为“两条命令”；删掉“模块顺序与源文件不同”；import 去掉未使用的 `json`；演练数字改为 569／3204；补 spec 可重建说明。

## 审核状态

- 第 1 版：P1/P3/P4 NEEDS_MODIFICATION（空行保留与演练冲突）。
- 第 2 版：待复核。
