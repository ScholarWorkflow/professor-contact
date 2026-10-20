# 迁移命令划分：migrate-v3 的计划与执行（执行计划）

## 版本、来源与状态

- Requirement revision: 第 1 版（2026-10-20 负责人要求；同一系列见 PR #95–#122）。
- Plan revision: 第 2 版。
- Proposed review status: 待审核。
- Target repository revision: 工作分支 `refactor-migrate`，父提交为堆栈末位 `refactor-stage4`（#122）的 head `2c81bae`。基准一律用 `git rev-parse origin/refactor-stage4` 动态取。
- 参考做法：`_stage4_commands.py`、`_stage5_commands.py`、`_stage3_commands.py` 的“按路径加载 + 工厂闭包 + runner 同名别名”。

## 目标与验收条件

| 编号 | 目标 | 验收条件 |
| --- | --- | --- |
| R1 | 4 个迁移定义离开 runner 顶层 | 4 个名字都不再在 `contact_state.py` 顶层定义；都出现在 `_migrate_commands.py` 的 `build()` 内；runner 有 4 个同名别名 |
| R2 | 搬移不改变逻辑 | 4 个定义体除缩进外逐字相同；非内建自由名字全部来自 `build()` 的 16 个 keyword-only 参数、同批定义或模块 import |
| R3 | 依赖显式注入，模块不反向依赖 runner | `_migrate_commands.py` 不 `import contact_state`、不按路径加载 runner、不做动态导入、不碰 `sys.path`／`sys.modules` |
| R4 | 绑定点合法 | 绑定块放在 `cmd_migrate_apply` 结束（2889）之后；16 个注入名里最晚的是 `apply_ready_entry`（2717） |
| R5 | 其余行为不变 | 不改常量值、CLI 子命令、帮助文本、Nix 布局与测试文件；`contact_state.py --help` 与父提交逐字节相同 |
| R6 | 接缝可核对 | `git diff --ignore-blank-lines -U0` 只出现加载块、绑定块、定义删除；probe 里合并出的三处空行块（4／6／3 行）收敛为 2；父提交自带的 6 行块（@2431–2436）保持原尺寸 |

## 范围：4 个定义、222 行

| 定义 | 行区间 | 行数 |
| --- | --- | --- |
| `migration_source_fingerprint` | 2505–2526 | 22 |
| `migrate_entry_for_professor` | 2553–2676 | 124 |
| `cmd_migrate_plan` | 2679–2714 | 36 |
| `cmd_migrate_apply` | 2850–2889 | 40 |

合计 222 行，落在四段。

### 需要注入的 16 个名字

`atomic_json@57`、`emit@60`、`fail@65`、`SCHEMA@328`、`MANAGED_BY@346`、`INPUT_PACK@378`、`CANDIDATES_MD@384`、`GAP_STATUSES@395`、`now_utc@457`、`sha256_bytes@458`、`sha256_obj@460`、`read_json_file@464`、`load_sidecar@572`、`read_legacy_index@2496`、`classify_direction@2529`、`apply_ready_entry@2717`。

最晚的是 `apply_ready_entry`（2717），早于绑定点（2890）。

### CLI 接线

`migrate-v3` 子命令用 `--plan`／`--apply` 分派：`set_defaults(func=lambda a: cmd_migrate_plan(a) if a.plan and not a.apply else cmd_migrate_apply(a))`。两个命令搬走后，这个 lambda 经别名解析，不需要改接线。

## 设计

新模块 `_migrate_commands.py`，一次 `build()`：16 个 keyword-only 参数、4 个成员；加载块锚点取 `SCHEMA = 1`（328）所在行；绑定块插在 `cmd_migrate_apply` 之后。

- 模块 import（按 AST 实测并补工厂需要）：`from pathlib import Path`、`import json`、`import os`、`import re`、`import types`；另有模板固定的 `from __future__ import annotations`。

### 取舍

1. **只搬两个 `cmd_migrate_*`**：`migrate_entry_for_professor`（124 行）是它们的主体，留下等于没拆。
2. **与 Stage 4 的迁移命令合并**：`cmd_stage4_migrate_local` 已在 #122 搬走，职责不同（Stage 4 的本地写入 vs 迁移 v3 的旧库转换），合并会混淆归属。
3. **4 个一起搬（选中）**：它们是一条“扫描旧库 → 构造条目 → 计划 → 执行”的链。

## 实施步骤

0. 从干净基线开始：`git status` 确认只有本次改动；还原演练产物到 `2c81bae` 再开始。
1. 用 `/tmp/pc-stage2-tools/extract_batch_v4.py`（144 行，sha256 `f47586be…`）加 spec（生成后把 probe 的 `_migrate_commands.py` 与 `contact_state.probe.py` 复制回工作树的 `scripts/` 再继续） `/tmp/pc-stage15/spec-b15.json` 生成模块与 probe runner：模块名 `_migrate_commands`、4 个函数名、`constants: []`、`load_anchor` = `SCHEMA = 1`（328）、`bind_after_line` = 2889、16 个参数名、模块 import（`Path`、`json`、`os`、`re`、`types`）；`/tmp` 清理后可用本文的函数名、参数名与两个锚点重建 spec。
2. 删除 4 个定义（只删 AST 定义的 4 个行区间，段内空行保留并参与合并）；probe 里合并出的三处空行块（4／6／3）收敛为 2；父提交自带的 6 行块保持原尺寸。
3. 接缝核对：`git diff --ignore-blank-lines -U0` 只允许出现加载块、绑定块、定义删除；没有常量值、import、CLI、入口清单改动；空行用只读脚本比对。
4. 逐字核对：4 个定义的 AST（忽略 docstring）与基线相同；docstring 整行核对；定义内注释用文本比对。
5. 把模板里的“Stage-2 helper module”改成“Migration helper module”（模块 docstring 与 runner 加载块注释各一处）。
6. 运行测试计划全部编号；提交实现与文档，推送分支，开 PR（base 为 `refactor-stage4`）。

## 验证方式

- 结构／AST 等价：`compare_stage2_batch_v2.py`（94 行，sha256 `1ba8c0f4…`）对 4 个名字做 T0–T3，预期 **28 条 `OK`**（T0 3、T1 9、T2 7、T3 9）。
- 行为：`TestMigrate` 的 6 个既有方法（见测试计划 T4）。
- 仓库既有 CI 照常执行，不作为本批必测项。

## 不纳入本批范围

| 未纳入项 | 原因 |
| --- | --- |
| `read_legacy_index`／`classify_direction`／`apply_ready_entry`／`load_sidecar` 这 4 个 helper | 本批按引用注入 |
| Stage 5 的 17 个组装/渲染 helper | 后续批次 |
| 常量值、CLI、帮助文本、Nix 布局、测试文件 | 本批只做搬移 |

## 风险与反例

1. **`migrate-v3` 的 lambda 接线**：`set_defaults(func=lambda a: cmd_migrate_plan(a) if ... else cmd_migrate_apply(a))` 在 `build_parser()` 里只是**创建**这个 lambda、不调用函数；真正调用发生在 `main()` 的 `args.func(args)`，那时别名已建立。
2. **绑定点必须晚于 `apply_ready_entry`（2717）**：放早会在 `build()` 调用时因 `apply_ready_entry` 还没定义而 `NameError`。
3. **四段之间夹着其它定义**（`classify_direction` 2529–2550、`apply_ready_entry` 2717–2847）：按 AST 定义删除即可，不会误删它们。
4. **docstring**：4 个定义都没有 docstring（`without_doc=4`），核对脚本应输出 `with_doc=0`，这是基线事实、不是丢失。
5. **空行**：probe 里合并出 4／6／3 三块，需全部收敛为 2；父提交自带的 6 行块必须原样保留。

## 实施前演练

按同一 spec 用 v4 生成、改掉模板文案并手工收敛空行后：模块 270 行、runner 3013 行；`--help` 与父提交逐字节相同；A/B 28 条 `OK`；docstring `total=4 with_doc=0 multi=0 clean_equal=0 without_doc=4 missing=0 mismatched=0`；T4 6 个方法、T5 2 个方法通过；runner 侧 4 个 hunk、diff `+37 −228`。

## 修订记录

- 第 1 版：首次提交（含演练实测数据）。
- 第 2 版：按审核的非阻断意见修正——风险 3 改成夹在四段之间的实际定义（`classify_direction`、`apply_ready_entry`）、风险 2 改成 `NameError` 而非“闭包参数缺失”、风险 1 说明 lambda 只创建不调用、不纳入清单补 `load_sidecar`、步骤 1 补“把 probe 产物复制回工作树再收敛”。

## 审核状态

- 第 1 版：P1–P4 全 PASS，`Plan conclusion: APPROVED`。
- 第 2 版：记录层修订，待复核。
