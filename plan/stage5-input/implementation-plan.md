# Stage 5 划分第一批：输入发现与候选选择（执行计划）

## 版本、来源与状态

- Requirement revision: 第 1 版（2026-10-20 负责人要求；同一系列见 PR #95–#119）。
- Plan revision: 第 4 版。
- Proposed review status: 待审核。
- Target repository revision: 工作分支 `refactor-stage5-input`，父提交为堆栈末位 `refactor-stage3-commands`（#119）的 head `f8be30d`。基准一律用 `git rev-parse origin/refactor-stage3-commands` 动态取。
- 参考做法：`_stage3_commands.py`、`_stage3_validation.py`、`_stage2_*`、`_contact_*` 的“按路径加载 + 工厂闭包 + runner 同名别名”。

## 目标与验收条件

| 编号 | 目标 | 验收条件 |
| --- | --- | --- |
| R1 | 13 个 Stage 5 输入层定义离开 runner 顶层 | 13 个名字都不再在 `contact_state.py` 顶层定义；都出现在 `_stage5_input.py` 的 `build()` 内；runner 有 13 个同名别名 |
| R2 | 搬移不改变逻辑 | 13 个定义体除缩进外逐字相同；非内建自由名字全部来自 `build()` 的 11 个 keyword-only 参数、同批定义或模块 import |
| R3 | 依赖显式注入，模块不反向依赖 runner | `_stage5_input.py` 不 `import contact_state`、不按路径加载 runner、不做动态导入、不碰 `sys.path`／`sys.modules` |
| R4 | 绑定点早于所有使用方 | 绑定块放在 `cmd_stage5_partition_choices`（2846）之后、`cmd_stage5_plan`（2849）之前；`cmd_stage5_plan` 实际用本批 5 个名字（`stage5_choices_by_id`、`stage5_local_pack`、`stage5_mode`、`stage5_output_id`、`stage5_pack_owner`），`cmd_stage5_finalize` 用 7 个 |
| R5 | 其余行为不变 | 不改常量值、CLI 子命令、帮助文本、Nix 布局与测试文件；`contact_state.py --help` 与父提交逐字节相同 |
| R6 | 接缝可核对 | `git diff --ignore-blank-lines -U0` 只出现加载块、绑定块、定义删除；删除后合并出的三处空行块（8 行、20 行、3 行）收敛为 2；父提交自带的两处（3 行、6 行）保持原尺寸 |

## 范围：13 个定义、492 行

| 定义 | 行区间 | 行数 |
| --- | --- | --- |
| `stage5_output_peers` | 409–441 | 33 |
| `stage5_output_paths` | 444–457 | 14 |
| `stage5_output_id` | 460–461 | 2 |
| `select_stage5_email` | 2386–2401 | 16 |
| `stage5_mode` | 2404–2408 | 5 |
| `stage5_pack_owner` | 2411–2431 | 21 |
| `stage5_local_pack` | 2434–2478 | 45 |
| `stage5_choices_rows` | 2481–2498 | 18 |
| `stage5_choices_by_id` | 2501–2570 | 70 |
| `stage5_list_input_rows` | 2573–2619 | 47 |
| `cmd_stage5_list_inputs` | 2622–2640 | 19 |
| `stage5_partition_pack_spec` | 2643–2697 | 55 |
| `cmd_stage5_partition_choices` | 2700–2846 | 147 |

合计 492 行，分两段（409–461 与 2386–2846）。

### 需要注入的 11 个名字

`emit@60`、`fail@65`、`soft_exit@66`、`STAGE4_LOCAL_SCHEMA@325`、`EMAIL_PACK_KIND@332`、`EMAIL_PACK@344`、`sha256_text@478`、`read_json_file@483`、`professor_dir_containment_error@484`、`require_professor_dir_under_program@485`、`filename_component@490`。

最晚的一个在 490 行，远早于绑定点（2847）。

### 与第二批的边界

第二批搬 `cmd_stage5_plan`（190）、`cmd_stage5_finalize`（268）、`stage5_recipient_authority`（25）、`cmd_stage5_rebuild_overview`（89）、`cmd_stage5_record_validation`（60），合计 632 行。实际依赖：`cmd_stage5_plan` 用 `stage5_local_pack`／`stage5_mode`／`stage5_pack_owner`／`stage5_choices_by_id`／`stage5_output_id`；`cmd_stage5_finalize` 用上面前五个再加 `stage5_output_peers`／`stage5_output_paths`（共 7 个：local_pack、mode、pack_owner、choices_by_id、output_id、output_peers、output_paths）；`cmd_stage5_rebuild_overview` 只用 `stage5_pack_owner`；`stage5_recipient_authority` 与 `cmd_stage5_record_validation` 不依赖本批。所以本批先做。`stage5_partition_pack_spec` 只服务本批的 `cmd_stage5_partition_choices`，与第二批无关。

## 设计

新模块 `_stage5_input.py`，一次 `build()`：11 个 keyword-only 参数、13 个成员；加载块锚点取 `SCHEMA = 1`（292）所在行；绑定块插在 `cmd_stage5_partition_choices` 之后、`cmd_stage5_plan` 之前。

### 取舍

1. **一次搬完 18 个 Stage 5 定义（1124 行）**：单批过大，且 plan／finalize 各近 200–270 行，与输入发现耦合弱。
2. **按 helper／命令拆**：`stage5_local_pack` 等 helper 同时服务两条命令，拆开会跨模块。
3. **按“输入发现与候选选择 vs 计划与终稿”拆（选中）**：本批 13 个定义做读取、规范化、选择映射，以及 `cmd_stage5_partition_choices` 的 `--out` 传输文件写出，边界清楚。

## 实施步骤

0. 从干净基线开始：`git status` 确认只有本次改动；工作树里遗留的演练产物（`_stage5_input.py` 与改过的 runner）要还原到 `f8be30d` 再开始，否则第 2 步会“已无定义可删”。
1. 用 `/tmp/pc-stage2-tools/extract_batch_v4.py`（144 行，sha256 `f47586beece5641b6a3a4308a9d26c1b55bda6592fc04329bf867dd1ada90273`）加 spec `/tmp/pc-stage12/spec-b12.json` 生成模块与 probe runner：模块名 `_stage5_input`、13 个函数名、`constants: []`、`load_anchor` = `SCHEMA = 1`（292）、`bind_after_line` = 2846、11 个参数名、模块 import（`Path`、`Any`、`json`、`os`、`types`；其中 `Any`／`os` 在 13 个定义里没有直接引用，是模板脚手架，保留不影响行为）。
2. 删除 13 个定义（只删 AST 定义的 13 个行区间，段内空行保留并参与合并）；把删除后合并出来的三处空行块（8 行、20 行、3 行）收敛为 2；父提交自带的两处（3 行、6 行）保持原尺寸。
3. 接缝核对：`git diff --ignore-blank-lines -U0` 只允许出现加载块、绑定块、定义删除；没有常量值、import、CLI、入口清单改动；空行用只读脚本比对。
4. 逐字核对：13 个定义的 AST（忽略 docstring）与基线相同；docstring 整行核对；定义内注释用文本比对。
5. 把模板里的“Stage-2 helper module”改成“Stage-5 helper module”（模块 docstring 与 runner 加载块注释各一处）。
6. 运行测试计划全部编号；提交实现与文档，推送分支，开 PR（base 为 `refactor-stage3-commands`）。

## 验证方式

- 结构／AST 等价：`/tmp/pc-stage2-tools/compare_stage2_batch_v2.py`（94 行，sha256 `1ba8c0f4…`）对 13 个名字做 T0–T3，预期 **73 条 `OK`**（T0 3、T1 27、T2 16、T3 27）。
- 行为：`stage5-list-inputs` 与 Stage 5 计划／终稿路径的既有测试方法（见测试计划 T4）；`stage5-partition-choices` 没有既有行为用例，只有 T2 的 AST 等价（T1/T3 佐证位置与接口）。
- 仓库既有 CI 照常执行，不作为本批必测项。

## 不纳入本批范围

| 未纳入项 | 原因 |
| --- | --- |
| `cmd_stage5_plan`／`cmd_stage5_finalize`／`stage5_recipient_authority`／`cmd_stage5_rebuild_overview`／`cmd_stage5_record_validation` | 第二批 |
| Stage 4、迁移命令、剩余共享 helper | 后续批次 |
| 常量值、CLI、帮助文本、Nix 布局、测试文件 | 本批只做搬移 |

## 风险与反例

1. **两段相隔很远**（409–461 与 2386–2846）：按 AST 定义删除即可，不会误删中间的 Stage 4 与其它 Stage 5 代码。
2. **partition 命令没有既有行为用例**：`cmd_stage5_partition_choices` 由 `build_parser` 注册为 CLI 子命令，`stage5_partition_pack_spec` 只被这条命令调用；仓库里没有测试驱动 `stage5-partition-choices`，所以这两段只有结构等价覆盖（测试计划 T4 已列为已知限制）。
3. **`stage5_output_*` 只有 2–33 行**，容易被当成“太小的 helper 不值得搬”，但它们是 `cmd_stage5_finalize` 与仍留在 runner 的 `humanized_paths` 的输出路径来源（`stage5_output_id` 另被 `cmd_stage5_plan` 使用；`record_validation` 不引用它们），留在 runner 会让第二批再注一遍。
4. **空行**：删除后合并出 8／20／3 三块，需收敛为 2；父提交自带的两处——3 行（1771–1773）与 6 行（3939–3944）——必须原样保留。注意绑定块插入本身会形成一处新的 3 行块（probe 里 2396–2398，位于 13 个别名之后、`cmd_stage5_plan` 之前），它要收敛为 2，不要和保留的 3 行块混为一谈。
5. **docstring**：13 个里 10 个有、全是多行；核对要读整行摘要（`total=13 with_doc=10 multi=10`）。
6. **模板文案**：提取器默认写“Stage-2 helper module”，必须改成 Stage 5，否则新模块与加载块注释会误导。

## 实施前演练

按同一 spec 用 v4 生成、改掉模板文案并手工收敛空行后：模块 553 行、runner 4237 行；`--help` 与父提交逐字节相同；A/B 73 条 `OK`；docstring `total=13 with_doc=10 multi=10 clean_equal=10 without_doc=3 missing=0 mismatched=0`；T4 10 个方法、T5 2 个方法通过；runner 侧 4 个 hunk。

## 修订记录

- 第 1 版：首次提交（含演练实测数据）。
- 第 2 版：按第一关意见修正——R4 改成 `cmd_stage5_plan` 实际使用的 5 个名字；与第二批的边界改成 `stage5_choices_by_id`／`stage5_pack_owner`，并说明 `stage5_partition_pack_spec` 只服务本批；风险补“partition 命令没有既有行为用例”。
- 第 3 版：按计划审核的 B1／B2 修正——与第二批的依赖改成实际清单（`cmd_stage5_plan` 5 个、`cmd_stage5_finalize` 7 个、`rebuild_overview` 1 个，`recipient_authority`／`record_validation` 不依赖本批）；`stage5_output_*` 的归属改为 `cmd_stage5_finalize` 与 `humanized_paths`（`record_validation` 不引用）；风险 3 改用父提交行号并把绑定块形成的 3 行块单独说明；第 2 步写明“只删 13 个行区间、段内空行参与合并”；R2 改为“非内建自由名字”；取舍 3 补 `--out` 写传输文件；注明 `Any`／`os` 是脚手架 import。
- 第 4 版：按第一关复核的可改进项——结构等价表述改为“T2 的 AST 等价（T1/T3 佐证）”、修订记录按版本排序；B1-b 已改为“前五个 + peers/paths”。

## 审核状态

- 第 1 版：P1 NEEDS_MODIFICATION（B1／B2 依赖关系写错）。
- 第 2 版：B1 主体已改，B1-b（finalize 用 7 个名字）与空行归属仍需修正。
- 第 3 版：B1-b 未闭合（finalize 列 6 个）。
- 第 4 版：P1–P4 全 PASS，`Plan conclusion: APPROVED`。
