# 共享基础层划分第一批：哈希／时间／文本／方向身份／托管文件（执行计划）

## 版本、来源与状态

- Requirement revision: 第 1 版（2026-10-20 负责人要求：把 `contact_state.py` 收敛为 CLI 分发与确有调用方依赖的兼容入口，按 PR 分批交付；同一系列见 PR #95–#114）。
- Plan revision: 第 3 版。
- Proposed review status: 待审核。
- Target repository revision: 工作分支 `refactor-shared-base`，父提交为分支链末位 `refactor-stage2-render`（#114）的 head `cf979ab`。坐标若在链上偏移，按函数名与 AST 重新定位。
- 参考做法：同目录 `_contact_io.py`、`_contact_evidence.py`、`_stage3_render.py`、`_stage3_handoff.py` 与六个 `_stage2_*.py` 的“按路径加载 + 工厂闭包 + runner 同名别名”。

## 目标与验收条件

| 编号 | 目标 | 验收条件 |
| --- | --- | --- |
| R1 | 40 个共用基础件离开 runner 顶层 | 40 个名字都不再在 `contact_state.py` 顶层用 `def` 定义；都出现在 `_contact_base.py` 的 `build()` 内；runner 有 40 个同名别名 |
| R2 | 搬移不改变逻辑 | 40 个定义体除缩进外逐字相同；自由名字全部来自 `build()` 的 7 个 keyword-only 参数、同批定义或模块自身 import |
| R3 | 依赖显式注入，模块不反向依赖 runner | `_contact_base.py` 不 `import contact_state`、不按路径加载 runner、不做动态导入、不碰 `sys.path`／`sys.modules` |
| R4 | 绑定点早于所有使用方 | 绑定块放在 `save_projections` 之后、`_stage2_facts.build(...)` 之前；六个 stage 模块与 runner 内其它调用点的运行期引用都在其后 |
| R5 | 其余行为不变 | 不改常量值、CLI 子命令、帮助文本、Nix 布局与测试文件；`contact_state.py --help` 与父提交逐字节相同 |
| R6 | 接缝可核对 | `git diff --ignore-blank-lines -U0` 只出现“加载块”“绑定/别名块”“40 个定义删除”三类 hunk；删除后遗留的空行收敛为 2 行，基线自带的空行块保持不变 |

## 范围：40 个定义、341 行

| 分组 | 定义（行区间） | 行数 |
| --- | --- | --- |
| 时间与哈希 | `now_utc` 354–355、`sha256_bytes` 358–359、`sha256_text` 362–363、`sha256_obj` 366–367 | 8 |
| 文本 | `normalized_quote` 370–371、`quote_id` 374–375、`text_tokens` 417–425、`title_tokens` 428–429、`truncate` 412–414 | 18 |
| 路径与读取 | `rel_path` 432–436、`filename_component` 439–442、`load_json` 378–380、`read_json_file` 383–389、`professor_dir_containment_error` 392–400、`require_professor_dir_under_program` 403–409、`safe_result_file` 445–447 | 38 |
| 方向身份与指纹 | `direction_machine_id` 450–470、`facts_direction_id` 473–486、`cross_group_id` 489–491、`pack_paper_index` 494–496、`direction_papers` 499–516、`paper_digest` 986–1002、`sidecar_sha` 1005–1008、`gap_fingerprint` 1011–1018、`candidate_fingerprint` 1021–1022、`direction_relevant_keys` 1025–1040、`direction_provisional_member_keys` 1043–1065、`pack_direction_relevant_keys` 1068–1084、`direction_candidate_keys` 1087–1099、`selected_candidate_union` 1102–1119、`direction_fingerprint` 1122–1143 | 199 |
| 托管文件与投影 | `render_frontmatter` 1146–1149、`split_frontmatter` 1152–1166、`managed_conflict` 1169–1181、`managed_write` 1184–1191、`managed_write_raw` 1194–1205、`projection_conflict` 1208–1217、`projection_write` 1220–1227、`load_projections` 1230–1235、`save_projections` 1238–1239 | 78 |

合计 40 个定义、341 行；分两段连续区间（354–516、986–1239），中间 519–984 的输入包规范化、候选状态与 Stage 5 输出 helper 留给后续批次。

### 需要注入的 7 个名字

`atomic_write@56`（`_contact_io.atomic_write` 的别名）、`atomic_json@57`（`_contact_io.atomic_json` 的别名）、`fail@65`（`_contact_io.fail` 的别名）、`MANAGED_BY@262`、`DIRECTION_IDENTITY_VERSION@278`、`PROJECTIONS_FILE@304`、`VERIFY_TIMESTAMP_FORMAT@341`。

### 使用方

- 六个 stage 模块的 `build()` 实参：`_stage2_facts`（1244–1281，36 个实参里有 15 个是本批名字）、`_stage2_resolve`（1308）、`_stage2_preflight`（1422）、`_stage2_render`（1475）、`_stage2_finalize`（1510）、`_stage2_validation`（6155）。
- 留在 runner 的输入包／候选状态／Stage 3–5 函数：`normalize_input_pack`、`normalize_candidate_state`、`cmd_stage3_*`、`cmd_stage4_*`、`cmd_stage5_*` 等，运行期全部经绑定块之后的别名解析。

## 设计

新模块 `_contact_base.py`，一次 `build()`：

```text
_contact_base = _contact_base_module.build(
    atomic_write=atomic_write, atomic_json=atomic_json, fail=fail,
    MANAGED_BY=MANAGED_BY, DIRECTION_IDENTITY_VERSION=DIRECTION_IDENTITY_VERSION,
    PROJECTIONS_FILE=PROJECTIONS_FILE, VERIFY_TIMESTAMP_FORMAT=VERIFY_TIMESTAMP_FORMAT)
now_utc = _contact_base.now_utc
... 40 个别名 ...
```

- `build()` 返回 40 个成员，顺序与 runner 里原定义顺序一致，便于逐字核对。
- 加载块锚点取 `SCHEMA = 1` 所在行（244），即插在 `_STAGE2_FACTS_*`（224–230）之后、`SCHEMA = 1` 之前，与其余 `_stage2_*` 加载块相邻；写法照 `_CONTACT_IO_*`。
- 绑定块放在 `save_projections` 之后、`_stage2_facts.build(...)` 之前：这是第一个消费方（`_stage2_facts` 用 15 个本批名字）之前、且在本批最后一个定义之后。
- 模块 import（实测；`timedelta` 本批未用，保留与 runner 同一 import 行）：`from datetime import datetime, timedelta, timezone`、`from pathlib import Path`、`from typing import Any`、`import hashlib`、`import json`、`import os`、`import re`、`import types`、`import unicodedata`。

### 取舍

1. **拆成两个模块（哈希/IO 与方向身份）**：本批 341 行、绑定环不复杂，拆两个会让 runner 多一套加载与绑定代码，收益不抵成本，否决。
2. **把中间 519–984 的输入包规范化一起搬**：那一组的依赖方向与本批相反（`normalize_input_pack` 用 `sha256_obj`／`direction_*`），同批搬会形成更大的注入面与更长的评审，留到下一批，否决。
3. **一个模块 `_contact_base.py`**（选中）：40 个名字都是“每个 stage 都直接用”的基础件，放一起后六个 stage 模块的注入名字会普遍减少，后续拆 Stage 3/4/5 时收益最大。

## 实施步骤

1. 用 `/tmp/pc-stage2-tools/extract_batch_v3.py`（141 行，sha256 `1536b8bd5cad8d46800ea2832479f12a959f3b6e0a5dc06bb3e93d760d505d31`；比第 1–7 批用的 v2 多一个 `bind_after`，因为本批的插入点前一个是 `save_projections`、后面紧跟的是 `_stage2_facts = …build(` 赋值语句而不是函数定义）加新 spec `/tmp/pc-stage8/spec-b8.json` 生成模块与 probe runner：模块名 `_contact_base`、40 个函数名、`constants: []`、`load_anchor` = `SCHEMA = 1` 所在行（加载块落在其它加载块之后）、`bind_after` = `save_projections`、7 个参数名、模块 import（`datetime`、`Path`、`Any`、`hashlib`、`json`、`os`、`re`、`types`、`unicodedata`）。
2. 删除 40 个定义（两段区间，按 AST 行区间），重构后收敛三处自造空行：第一段 44 行、第二段 38 行、绑定块与 `_stage2_facts` 注释之间 3 行，都收敛为 2 行；父提交自带的 6 处长空行块（6／4／4／10／3／6 行）保持原样。

> 演练实测：模块 456 行、runner 6730 行；`--help` 与父提交逐字节相同；A/B 208 条 `OK`（T0 3、T1 81、T2 43、T3 81）；docstring 13 个有（9 个多行）同文、27 个原本没有；T4 10 个方法、T5 2 个方法通过；runner 侧接缝 3 个 hunk：`@@ -243,0 +244,12 @@`（加载块 12 行）、`@@ -354,165 +365,0 @@`（第一段 21 个定义删除）、`@@ -986,254 +833,52 @@`（第二段 19 个定义删除与绑定块 52 行），diff 为 `+63 −418`。
3. 接缝核对：`git diff --ignore-blank-lines -U0` 只允许出现加载块、绑定块、两段定义删除；没有常量值、import、CLI、入口清单改动。
4. 逐字核对：40 个定义的 AST（忽略 docstring）与基线相同；docstring 用只读脚本核对（清洗后同文）。
5. 运行测试计划全部编号；提交实现与文档，推送分支，开 PR（base 为分支链上一位 `refactor-stage2-render`）。

## 验证方式

- 结构／AST 等价：`/tmp/pc-stage2-tools/compare_stage2_batch_v2.py`（94 行，sha256 `1ba8c0f49346b1fa78c34fbeec4d82cdab206ebef6cbf1b629769f9e5e4346b6`）对 40 个名字做 T0–T3 检查，预期 **208 条 `OK`**（T0 3、T1 81、T2 43、T3 81）。base 目录必须是父提交 `cf979ab` 的导出——**`/tmp/pc-stage2-tools/base-wt` 是拆分前的旧快照（11894 行），不能直接用**，须重新 `git archive cf979ab`。
- 行为：覆盖哈希／文本／方向身份／托管写入的既有测试方法（清单见测试计划 T4）。
- 仓库既有 CI 照常执行，不作为本批必测项。

## 不纳入本批范围

| 未纳入项 | 原因 |
| --- | --- |
| 输入包规范化与迁移 helper（`normalize_input_pack`、`_migrate_v1_*`、`_slice_gap_directions`、`_canonical_paper_record`、`_merge_canonical_paper` 等） | 下一批；它们反向依赖本批的哈希与方向身份 |
| 候选状态（`normalize_candidate_state`、`_strict_candidate_shape`、`strict_candidate_state`、`load_candidate_state`）与 Stage 5 输出 helper | 后续批次 |
| Stage 3／4／5 主体与迁移命令 | 后续批次 |
| 常量值、CLI、帮助文本、Nix 布局、测试文件 | 本批只做搬移 |

## 风险与反例

1. **方向身份函数之间的相互依赖**：`direction_fingerprint` 用 `direction_relevant_keys` 与 `sha256_obj`、`paper_digest` 用 `read_json_file`；这些都同批搬入，闭包内自洽。反例是若漏掉某个同批名字，导入期不报错、运行期才 `NameError`，靠 T3 的签名与调用检查与 T4 覆盖暴露。
2. **两段区间之间夹着别的定义**：本批是 354–516 与 986–1239 两段，519–984 保持不动；实施前用 AST 确认两段内的顶层定义恰好是这 40 个。
3. **绑定块位置**：必须晚于 `save_projections`（1239）且早于 `_stage2_facts.build`（1244）。父提交里两者只隔 4 行，插入时要保证前后各 2 个空行且不挤压 `_stage2_facts` 的注释。
4. **`fail`／`atomic_*` 是 `_contact_io` 的别名**：注入的是 runner 里的同名别名（第 56／57／65 行），值与原引用相同；本批不新增第二条错误通道。
5. **docstring 缩进**：搬入 `build()` 后 docstring 续行加 4 空格，否则 `inspect.cleandoc` 不同。

## 实施前演练

按同一 spec 演练了一遍并把产物落到工作树复验：模块 456 行、runner 6730 行；`--help` 与父提交逐字节相同；A/B 208 条 `OK`；docstring 核对 `total=40 with_doc=13 multi=9 clean_equal=13 without_doc=27 missing=0 mismatched=0` 与 `DOCSTRING CHECKS PASS`；T4 10 个方法 `OK`、T5 2 个方法 `OK`；runner 侧只剩 3 个 hunk。演练第一次漏了 `import os`（`rel_path` 用 `os.path.relpath`），10 个 T4 方法全挂，补上后全绿——因此模块 import 一栏已按实测写全。

## 修订记录

- 第 1 版：首次提交。
- 第 2 版：按演练结果修正——提取器改为带 `bind_after` 的 v3；模块 import 按实测补 `os`／`hashlib`／`json`／`re`／`unicodedata`；补第 2 步的空行收敛细节（44／38／3 → 2）与演练实测数据。

## 审核状态

- 第 1 版：待计划审核。
- 第 2 版：P1 NEEDS_MODIFICATION（分组行数 4 处、消费方实参数 16→15、加载块位置表述）；已按实测改：行数 8/18/38/199/78、`_stage2_facts` 用 15 个本批名字、加载块锚点写成“在 `_STAGE2_FACTS_*` 之后、`SCHEMA = 1` 之前（244 行）”；并补 3 个 hunk 的准确构成、`timedelta` 未用的说明、PR 系列引用与“base-wt 是旧快照”的警告。
- 第 3 版：按复核结果更正分组行数、消费方实参数与加载块位置描述，并补 3 个 hunk 构成、`timedelta` 说明、PR 区间与 base-wt 警告；复核 P1–P4 全 PASS，`Plan conclusion: APPROVED`。
