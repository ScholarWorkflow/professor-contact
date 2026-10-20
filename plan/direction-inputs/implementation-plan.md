# 方向输入助手划分：profile、切片与跨组解析（执行计划）

## 版本、来源与状态

- Requirement revision: 第 1 版（2026-10-20 负责人要求；同一系列见 PR #95–#126）。
- Plan revision: 第 2 版。
- Proposed review status: pending。
- Target repository revision: 工作分支 `refactor-email-core` 之后的新分支 `refactor-direction-inputs`，父提交为 `972d4fd`（PR #126 的 head）。基准用 `git rev-parse origin/refactor-email-core` 动态取。
- 参考做法：`_stage4_commands.py`、`_candidate_validate.py`、`_email_core.py` 的“按路径加载 + 工厂闭包 + runner 同名别名”。

## 目标与验收条件

| 编号 | 目标 | 验收条件 |
| --- | --- | --- |
| R1 | 6 个方向输入定义离开 runner 顶层 | 6 个名字都不再在 `contact_state.py` 顶层定义；都出现在 `_direction_inputs.py` 的 `build()` 内；runner 有 6 个同名别名，且与模块同名属性是同一对象（`is` 成立）；别名的书写顺序不作契约 |
| R2 | 搬移不改变逻辑 | 6 个定义的 AST 相同（比较时忽略 docstring）；docstring 文本逐行相同；非内建自由名字全部来自 `build()` 的 7 个 keyword-only 参数（顺序同名对应）或模块 import（`Path`、`Any`、`json`） |
| R3 | 依赖显式注入，模块不反向依赖 runner | `_direction_inputs.py` 不 `import contact_state`、不按路径加载 runner、不做动态导入、不碰 `sys.path`／`sys.modules` |
| R4 | 绑定点在全部消费方之前 | 绑定块放在 `cmd_stage2_finalize` 别名（893）之后、`_candidate_validate` 的 `build()`（原 939）之前；父提交的 5 个 build 消费点是 939（`_direction_slices`@942）、1053（`profile_fingerprint`@1079）、1157（6 个全在 1193–1198）、1227（`profile_fingerprint`@1249）、1493（`load_profile_text`@1518），全部在绑定块之后，无需改动 |
| R5 | 参数与消费方一致 | `_direction_inputs.build` 收 7 个名字（`fail`、`sha256_bytes`、`truncate`、`PROFILE_INPUT_CHARS`、`direction_machine_id`、`direction_papers`、`cross_group_id`），全部在绑定块之前定义（最晚 `PROFILE_INPUT_CHARS`@469）；不新增无消费方的参数 |
| R6 | 其余行为不变 | 不改常量值、CLI 子命令、帮助文本、Nix 布局与测试文件；`--help` 与父提交逐字节相同（3221 字节，sha256 `d622b7e6…`） |
| R7 | 接缝可核对 | `git diff --ignore-blank-lines -U0` 对 `contact_state.py` 是 6 个 hunk：2 个插入与删除混合（`-896,8 +896,11`、`-905,7 +908,11`）、1 个纯插入（`-912,0 +920,6`，6 个别名）、3 个纯删除（`-914,2`、`-917,20`、`-956,60`）；默认上下文下是 2 个 hunk；净变更 +28 −97；`_direction_inputs.py` 是新增文件（130 行）；完整 diff 之外没有常量值、CLI、入口清单改动 |

## 范围：6 个定义 91 行

| 定义 | 行区间（父提交） | 行数 |
| --- | --- | --- |
| `profile_fingerprint` | 896–902 | 7 |
| `load_profile_text` | 905–911 | 7 |
| `_direction_slices` | 914–936 | 23 |
| `_cross_group_fresh` | 956–967 | 12 |
| `_parse_direction_id_list` | 970–977 | 8 |
| `_parse_cross_groups` | 980–1013 | 34 |

删除区间 896–1013 共 118 行，区间内保留 23 行：父提交自带的 `_candidate_validate` 绑定块 19 行（937–955）与 4 行空行（904、912、913、916，其中 916 落在 `_direction_slices` docstring 内、被 `git diff` 当作上下文保留）。区间内删除 95 行 = 90 行定义源码（6 个定义共 91 行，减去被 docstring 空行抵掉的 1 行）+ 5 行空行（903、968、969、978、979）；区间外删除 2 行（1014、1015 的空行）。合计删除 97 行 = 90 + 7 行空行，没有注释行被删除。

### 需要注入的 7 个名字

`fail@65`、`PROFILE_INPUT_CHARS@469`（最晚）、`sha256_bytes@506`、`truncate@515`、`direction_machine_id@521`、`cross_group_id@523`、`direction_papers@525`。

### 实测自由名字

| 定义 | 自由名字 |
| --- | --- |
| `profile_fingerprint` | `Path`, `sha256_bytes` |
| `load_profile_text` | `Path`, `truncate`, `PROFILE_INPUT_CHARS` |
| `_direction_slices` | `direction_machine_id`, `direction_papers` |
| `_cross_group_fresh` | 无 |
| `_parse_direction_id_list` | 无 |
| `_parse_cross_groups` | `Any`, `fail`, `cross_group_id`, `direction_machine_id`, `json` |

### 为什么这 6 个必须同批

`_direction_slices` 被 `_candidate_validate.build`（父提交 939，参数在 942）与 `_stage3_commands.build`（父提交 1157，参数在 1195）同时消费；`profile_fingerprint` 另有 3 个消费点（1079、1193、1249），`load_profile_text` 另有 2 个（1194、1518）。需求已定这 6 个同批，且 6 个别名都要出现在最早消费点 939 之前；为不拆开这 6 个连续定义，绑定块放在 896（这 6 个定义的起点）：6 个一起离开 runner，别名先出现，939 及其后的 4 个 build 才拿得到。

## 设计

新模块 `_direction_inputs.py`，一次 `build()`：7 个 keyword-only 参数、6 个成员；加载块与绑定块都插在父提交 896 之前（加载块先，绑定块后）；父提交 937–953 的 `_candidate_validate` 绑定块原样保留，位置随删除上移。

- 模块 import：`import json`、`import types`、`from pathlib import Path`、`from typing import Any`；另有模板固定的 `from __future__ import annotations`。
- `json` 与 `Any` 只被 `_parse_cross_groups` 使用，按“模块自持”原则放在模块里，不从 runner 注入。
- `PROFILE_INPUT_CHARS` 是 schema 常量，留在 runner，按关键字注入（与 `_email_core` 的 `EMAIL_SOURCE_HASH_FIELDS` 同做法）。

## 实施步骤

0. 从干净基线开始：`git status` 确认只有本次改动。
1. 用 `/tmp/pc-stage2-tools/extract_batch_v4.py`（144 行，sha256 `f47586beece5641b6a3a4308a9d26c1b55bda6592fc04329bf867dd1ada90273`）加 spec `/tmp/pc-stage20/spec-b20.json`（sha256 `002d9c03b9344e920a8509511b2bfd228ecec5dcc507bd9504e40aac3826ae3e`；内容为 6 个函数名、7 个参数、`load_anchor`=896、`bind_after_line`=895、`out_dir`=`/tmp/pc-stage20/probe`）生成模块与 probe runner。
2. 把模板里的“Stage-2 helper module”改成“Direction-input helper module”；模块 import 块后合并出的 4 行空行收敛为 2（与 `_email_core.py` 一致）。
3. 用 probe 的 `contact_state.probe.py` 覆盖 runner：6 个定义随之消失，probe 里合并出的 5 行（926）与 8 行（948）两处空行块收敛为 2；父提交自带的 6 行块（父提交 1584–1589，收敛后 1515–1520）保持原尺寸。
4. 接缝核对：`git diff --ignore-blank-lines -U0` 对 `contact_state.py` 是 6 个 hunk、默认上下文 2 个；没有常量值、CLI、入口清单改动。
5. 逐字核对：6 个定义的 AST（忽略 docstring）与基线相同；docstring 整行核对（3 个有、都是多行，9／3／6 行；3 个没有）；`--help` 逐字节相同。
6. 运行测试计划全部编号；提交实现与文档，推送分支，开 PR（base 为 `refactor-email-core`）。

## 验证方式

- 结构／AST 等价：`compare_stage2_batch_v2.py`（94 行，sha256 `1ba8c0f49346b1fa78c34fbeec4d82cdab206ebef6cbf1b629769f9e5e4346b6`）对 6 个名字做 T0–T3，预期 38 条 `OK`（T0 3、T1 13、T2 9、T3 13），另有 1 行 `ALL CHECKS PASS` 汇总。
- docstring：`check_docstrings_v3.py`（sha256 `31c8b208…`）预期 `total=6 with_doc=3 multi=3 clean_equal=3 without_doc=3 missing=0 mismatched=0`。
- 行为：跨方向组与 resolved-direction 的既有 4 个 CLI 测试方法（见测试计划 T4）。
- 仓库既有 CI 照常执行，不作为本批必测项。

## 不纳入本批范围

| 未纳入项 | 原因 |
| --- | --- |
| verify 链（`_fingerprint_failure_kind`、`_verify_diagnostic_failure`、`verify_state`）与 `canonical_professor_dir` | 下一批（约 105 行） |
| legacy 迁移 helper（`read_legacy_index`、`classify_direction`、`apply_ready_entry`） | 再下一批（约 160 行） |
| `gap_job_block`、`assemble_followup_draft`、`load_validator_results` | 依赖 `_stage5_commands` 的成员，单独一批 |
| stage1 三件套（692–750） | 已登记为注入给 `_stage2_preflight`，最后处理 |
| `build_parser`、`main` | 不搬移（CLI 入口） |
| 常量值、CLI、帮助文本、Nix 布局、测试文件 | 本批只做搬移 |

## 风险与反例

1. **绑定顺序**：把绑定块放到 `_candidate_validate` 之后，`_direction_slices` 别名在使用处还不存在（NameError）；放在 `PROFILE_INPUT_CHARS` 之前则注入到未定义常量。
2. **空行**：probe 在 926 与 948 各合并出 5 行、8 行空行块，需收敛为 2；父提交自带的 6 行块（`_stage2_validation` 绑定点之前）必须原样保留，否则会被误判成多余空行。
3. **hunk 口径**：6 个 hunk 是 `-U0` 口径且只对 `contact_state.py` 成立；默认上下文是 2 个，新增文件不计 hunk。
4. **docstring**：3 个有（`_direction_slices` 9 行、`_cross_group_fresh` 3 行、`_parse_cross_groups` 6 行），3 个没有（`profile_fingerprint`、`load_profile_text`、`_parse_direction_id_list`）；核对时不能用“全部都有”当预期。
5. **`_parse_cross_groups` 的 `fail`**：失败分支只在输入非法时触发，T4 的 4 个方法里只有 `test_cross_group_input_fail_closed` 覆盖它；缺这个方法，`fail` 注入传错也不会暴露。

## 实施前演练

按上述步骤生成并收敛空行后：模块 130 行、runner 2085 行（父提交 2154 行）；`--help` 与父提交逐字节相同（sha256 `d622b7e6…`）；A/B 38 条 `OK`；docstring `total=6 with_doc=3 multi=3 clean_equal=3`；diff `+28 −97`（`-U0` 下 6 个 hunk，默认上下文 2 个）；`test_stage3_direction_groups` 19 个方法全通过。演练时另外做过一次调用次数统计（插桩副本替换工作树模块、跑完恢复），用于挑选 T4 的 4 个方法，不作为必测步骤、也不进测试记录。

## 修订记录

- 第 1 版：首次提交（含演练实测数据）。
- 第 2 版：按计划审核意见校正删除行数（91 + 6 = 97）、消费方清单（5 个 build 点）、hunk 构成、docstring 事实（9／3／6 行、3 个没有）与别名口径（`is` 同一，不约束顺序）；A/B 计数写成“38 条 `OK` + 1 行汇总”；删去把插桩与进程内对照脚本当必测证据的说法（未获批准的新增设施，不作为本轮测试义务）。

## 审核状态

- 第 2 版：Proposed review status: pending（reviewer 已于 2026-10-21 给出 `Plan conclusion: APPROVED`，正式结论见其 Review record；第 1 版意见 B1、B2、B3、B9、B10、B13、B14、B15、B16、B19 已修订，复核意见 N1（删除构成明细）与 N2（同批理由的推导）已同版改正）。基线 sha 随 PR #126 rebase 由 `5489057` 更新为 `972d4fd`，rebase 前后 `git diff` 为空，代码与测量值不变。
