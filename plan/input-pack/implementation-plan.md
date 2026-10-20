# 共享基础层第二批：输入包规范化和候选状态（执行计划）

## 版本、来源与状态

- Requirement revision: 第 1 版（2026-10-20 负责人要求：`contact_state.py` 收敛为 CLI 分发与确有调用方依赖的兼容入口；同一系列见 PR #95–#116）。
- Plan revision: 第 2 版。
- Proposed review status: 待审核。
- Target repository revision: 工作分支 `refactor-input-pack`，父提交为堆栈末位 `refactor-shared-base`（#116）的 head `4ff8ff6`。**堆栈被 GitHub 自动 rebase 时，基准按父分支名重新取值（`git rev-parse origin/refactor-shared-base`），程序内容不变。**
- 参考做法：`_contact_io.py`、`_contact_evidence.py`、`_contact_base.py` 与六个 `_stage2_*.py` 的“按路径加载 + 工厂闭包 + runner 同名别名”。

## 目标与验收条件

| 编号 | 目标 | 验收条件 |
| --- | --- | --- |
| R1 | 11 个输入包／候选状态定义离开 runner 顶层 | 11 个名字都不再在 `contact_state.py` 顶层用 `def` 定义；都出现在 `_contact_pack.py` 的 `build()` 内；runner 有 11 个同名别名 |
| R2 | 搬移不改变逻辑 | 11 个定义体除缩进外逐字相同；自由名字全部来自 `build()` 的 14 个 keyword-only 参数、同批定义或模块自身 import |
| R3 | 依赖显式注入，模块不反向依赖 runner | `_contact_pack.py` 不 `import contact_state`、不按路径加载 runner、不做动态导入、不碰 `sys.path`／`sys.modules` |
| R4 | 绑定点早于所有使用方 | 绑定块放在 `_contact_base` 别名块之后、`_stage2_facts.build(...)` 之前；`load_input_pack` 的三个消费方（`_stage2_facts`／`_stage2_preflight`／`_stage2_validation`）都在其后 |
| R5 | 其余行为不变 | 不改常量值、CLI 子命令、帮助文本、Nix 布局与测试文件；`contact_state.py --help` 与父提交逐字节相同 |
| R6 | 接缝可核对 | `git diff --ignore-blank-lines -U0` 只出现“加载块”“绑定/别名块”“11 个定义删除”三类 hunk；删除后遗留的空行收敛为 2 行、基线自带的 6 处长空行块数量与长度不变（用只读脚本比对空行块，`--ignore-blank-lines` 看不到这一层）；定义内注释的逐字性用“基线源码片段 vs 模块内缩进 4 空格的片段”文本比对确认（AST 不含注释） |

## 范围：11 个定义、383 行

| 定义 | 行区间 | 行数 |
| --- | --- | --- |
| `_canonical_paper_record` | 373–378 | 6 |
| `_merge_canonical_paper` | 381–407 | 27 |
| `normalize_input_pack` | 410–486 | 77 |
| `load_input_pack` | 489–494 | 6 |
| `_migrate_v1_candidate` | 497–511 | 15 |
| `_slice_gap_directions` | 514–537 | 24 |
| `_migrate_v1_cross_group` | 540–586 | 47 |
| `normalize_candidate_state` | 589–672 | 84 |
| `load_candidate_state` | 675–685 | 11 |
| `_strict_candidate_shape` | 688–731 | 44 |
| `strict_candidate_state` | 734–775 | 42 |

合计 383 行，区间连续。HEAD 里 373 之前是 `_CANONICAL_PAPER_FIELDS`（368–370），之后 778–830 的 `stage5_output_*` 留给 Stage 5 批次；`_contact_base` 的加载与别名块在文件更下方（加载 243–255、别名 845–884）。

### 需要注入的 14 个名字

常量与别名（11 个）：`fail@65`、`soft_exit@66`、`INPUT_PACK_SCHEMA@281`、`CANDIDATE_STATE_SCHEMA@282`、`DIRECTION_IDENTITY_VERSION@290`、`STAGE3_GENERATOR_CONTRACT_VERSION@291`、`INPUT_PACK_KIND@293`、`CANDIDATE_STATE_KIND@294`、`INPUT_PACK@306`、`CANDIDATE_STATE@307`、`_CANONICAL_PAPER_FIELDS@368`。

同批之外、由第 8 批产出的别名（3 个）：`read_json_file@852`、`direction_machine_id@861`、`cross_group_id@863`。

### 使用方

- `_stage2_facts`（889–926，36 个实参里有 1 个本批名字 `load_input_pack`）、`_stage2_preflight`（build 调用 1067–1080，`load_input_pack` 实参在 1074）、`_stage2_validation`（build 调用 5800–5839，实参在 5818）。
- 留在 runner 的 `cmd_stage3_*`／`cmd_migrate_*` 等运行期经别名解析。

## 设计

新模块 `_contact_pack.py`，一次 `build()`：

```text
_contact_pack = _contact_pack_module.build(
    fail=fail, soft_exit=soft_exit, INPUT_PACK_SCHEMA=INPUT_PACK_SCHEMA, ... 14 个 keyword-only 实参 ...)
_canonical_paper_record = _contact_pack._canonical_paper_record
... 11 个同名别名 ...
```

- `build()` 返回 11 个成员，顺序与原定义顺序一致。
- 加载块锚点取 `SCHEMA = 1` 所在行（256），即插在其它模块加载块之后、`SCHEMA` 之前。
- 绑定块放在 `_contact_base` 别名块的最后一行（`save_projections = _contact_base.save_projections`，**884**）之后、`_stage2_facts_module.build(`（**889**）之前——885–886 是别名块后的空行、887–888 是原有注释；这样 `read_json_file`／`direction_machine_id`／`cross_group_id` 三个别名已经存在，且早于第一个消费方。spec 的 `bind_after_line` 用 884。
- 模块 import（按 AST 实测，只保留真正用到的）：`from pathlib import Path`、`from typing import Any`、`import types`；`datetime`／`timedelta`／`timezone`／`json`／`re` 在本批 11 个定义里 0 次引用，已从 spec 中去掉。

### 取舍

1. **与上一批合成一个模块**：`_contact_base` 已提交，改动它会牵动上一批的复核；且本批有 14 个注入参数、与基础件职责不同，否决。
2. **拆成“输入包”与“候选状态”两个模块**：3 个 v1 迁移函数只服务候选状态，但 `strict_candidate_state`／`load_candidate_state` 依赖 `load_input_pack`／`normalize_input_pack`，拆开就要在两个模块间再传一遍依赖，否决。
3. **一个模块 `_contact_pack.py`**（选中）：11 个定义是一条“读入 → 规范化 → 迁移 → 严格校验”的链，放一起最自然。

## 实施步骤

1. 用 `/tmp/pc-stage2-tools/extract_batch_v4.py`（144 行，sha256 `f47586beece5641b6a3a4308a9d26c1b55bda6592fc04329bf867dd1ada90273`；比 v3 多 `bind_after_line`，因为本批插入点前是别名赋值而不是函数定义）加 spec `/tmp/pc-stage9/spec-b9.json` 生成模块与 probe runner：模块名 `_contact_pack`、11 个函数名、`constants: []`、`load_anchor` = `SCHEMA = 1` 所在行、`bind_after_line` = 884（`_contact_base` 别名块最后一行）、14 个参数名、模块 import（`Path`、`Any`、`types`）。
2. 删除 11 个定义（按 AST 行区间），把删除后遗留的 24 行空行块与绑定块之后多出的 3 行空行块都收敛为 2 行；插入加载块与绑定块。
3. 接缝核对：`git diff --ignore-blank-lines -U0` 只允许出现加载块、绑定块、定义删除；没有常量值、import、CLI、入口清单改动。另做两项只读核对：① 空行块——用脚本统计基线与本批产物的 ≥3 行空行块，要求基线自带的 6 处数量与长度不变、只有删除处新增的 24 行块收敛为 2；② 注释逐字——把 11 个定义在基线的源码片段与模块内对应片段（去掉 4 空格缩进）做文本比对，确认定义内注释未变。
4. 逐字核对：11 个定义的 AST（忽略 docstring）与基线相同；docstring 用只读脚本核对。
5. 运行测试计划全部编号；提交实现与文档，推送分支，开 PR（base 为父分支 `refactor-shared-base`）。

## 验证方式

- 结构／AST 等价：`/tmp/pc-stage2-tools/compare_stage2_batch_v2.py`（94 行，sha256 `1ba8c0f49346b1fa78c34fbeec4d82cdab206ebef6cbf1b629769f9e5e4346b6`）对 11 个名字做 T0–T3 检查，预期 **63 条 `OK`**（T0 3、T1 23、T2 14、T3 23）。base 目录必须是父分支 head 的导出（**不要用 `/tmp/pc-stage2-tools/base-wt`，那是 11894 行的拆分前旧快照**）。
- 行为：覆盖输入包规范化、候选状态与 v1 迁移的既有测试方法（清单见测试计划 T4）。
- 仓库既有 CI 照常执行，不作为本批必测项。

## 不纳入本批范围

| 未纳入项 | 原因 |
| --- | --- |
| `stage5_output_peers`／`stage5_output_paths`／`stage5_output_id`（778–830） | Stage 5 批次 |
| Stage 3／4／5 主体与其余 helper | 后续批次 |
| 常量值、CLI、帮助文本、Nix 布局、测试文件 | 本批只做搬移 |

## 风险与反例

1. **绑定点依赖第 8 批的别名**：`read_json_file`／`direction_machine_id`／`cross_group_id` 由 `_contact_base` 提供；若插入点放早（例如放在 `strict_candidate_state` 之后），这三名字尚未定义，导入期 `NameError`。实施前用 AST 确认插入点在 `save_projections`（884）之后、`_stage2_facts_module.build(`（889）之前。
2. **11 个定义之间有相互调用**：`normalize_input_pack` 用 `_canonical_paper_record`／`_merge_canonical_paper`；`normalize_candidate_state` 用 `_migrate_v1_candidate` 与 `_migrate_v1_cross_group`（后者再用 `_slice_gap_directions`）；`strict_candidate_state` 用 `_strict_candidate_shape`、`load_input_pack`、`normalize_candidate_state`。同批搬入后在闭包内自洽，漏一个就会在 T4 暴露。
3. **区间连续性**：373–775 之间若夹着不属于本批的定义，整段删除会误删；实施前用 AST 确认区间内恰好 11 个定义。
4. **docstring 缩进**：搬入 `build()` 后 docstring 续行加 4 空格，否则 `inspect.cleandoc` 不同。
5. **堆栈 rebase 导致基准失效**：基准写成分支名 + 当前 SHA，并注明“rebase 后按分支名重新取值”。（第 7 批复核已因此返工过一次。）

## 实施前演练

按同一 spec 演练并把产物落到工作树复验：最终产物模块 441 行、runner 6367 行（中间 probe 为 444/6390，收敛两处自造空行后即最终值）；`--help` 与父提交逐字节相同；A/B 63 条 `OK`（T0 3、T1 23、T2 14、T3 23）；docstring `total=11 with_doc=10 multi=9 clean_equal=10 without_doc=1 missing=0 mismatched=0`；T4 10 个方法、T5 2 个方法通过。

## 修订记录

- 第 1 版：首次提交（含演练实测数据）。
- 第 2 版：按审核修正——绑定点统一为“最后别名 `save_projections` 884 之后、`_stage2_facts.build` 889 之前”（spec 的 `bind_after_line` 同步改 884，产物重新生成：模块 441 行、runner 6367 行，收敛两处自造空行后）；import 只保留 `Path`／`Any`／`types`；风险 2 的调用关系与取舍 2 的理由按实际依赖改写；补 373 前的真实上下文、36 个实参的两种口径、R6 的空行块与注释文本核对方法。

## 审核状态

- 第 1 版：P1 NEEDS_MODIFICATION（绑定点 886 与实际 884 不一致）。
- 第 2 版：P1–P4 全 PASS，`Plan conclusion: APPROVED`。
