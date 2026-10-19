# Stage 2 划分第六批：facts／gap／sidecar 数据层与两个上下文对象（执行计划）

## 版本、来源与状态

- Requirement revision: 第 1 版（2026-10-20 负责人要求：把 `contact_state.py` 收敛为 CLI 分发与确有调用方依赖的兼容入口，每个 stage 的主要逻辑拆成同目录内部模块，按 PR 分批交付）。
- Plan revision: 第 2 版。
- Proposed review status: **APPROVED**（`Plan conclusion: APPROVED`，2026-10-20，P1–P4 全 PASS；第 1 版的 P4 两条必改项已在第 2 版闭合）。
- Target repository revision: 工作分支 `refactor-stage2-context`，基线为集成提交 `b862dfa`（`7a59006` 上依次并入 #112、#110、#111 后的树）。本批实现提交在其之上；坐标在合并后若发生偏移，按函数名与 AST 重新定位，不按行号硬删。
- 参考做法：`_stage3_render.py`、`_contact_io.py`、`_contact_evidence.py`、`_stage3_handoff.py`、`_stage2_preflight.py`、`_stage2_resolve.py`、`_stage2_finalize.py`、`_stage2_validation.py` 的“按路径加载 + 工厂闭包 + runner 同名别名”写法。

## 目标与验收条件

| 编号 | 目标 | 验收条件 |
| --- | --- | --- |
| R1 | 18 个顶层定义整体离开 runner 顶层 | 18 个名字都不再在 `contact_state.py` 顶层用 `def`／`class` 定义；都出现在 `_stage2_facts.py` 的 `build()` 内；runner 有 18 个 `X = _stage2_facts.X` 别名 |
| R2 | 搬移不改变逻辑 | 18 个定义体除缩进（+4 空格）与 docstring 续行缩进外逐字相同；自由名字全部来自 `build()` 的 keyword-only 参数（36 个）或同批定义 |
| R3 | 依赖显式注入，模块不反向依赖 runner | `_stage2_facts.py` 不 `import contact_state`、不按路径加载 runner、不做动态导入、不碰 `sys.path`／`sys.modules`；36 个依赖全部由 runner 在 `build()` 调用处按同名实参注入 |
| R4 | 绑定点早于所有使用方 | 两条常量别名上移后，`build()` 调用位于 `_stage2_resolve.build`（使用 `Stage2Context`）之前，18 个别名在四个模块的 `build()` 调用之前 |
| R5 | 其余行为不变 | 不改常量值、CLI 子命令、帮助文本、Nix 布局与测试文件；`contact_state.py --help` 输出与基线逐字节相同 |

## 现状事实（`b862dfa`，runner 8191 行）

| 定义 | 种类 | 行 | 行数 |
| --- | --- | --- | --- |
| `sidecar_analysis_matches` | def | 1216–1233 | 18 |
| `sidecar_path_matches` | def | 1236–1248 | 13 |
| `load_sidecar` | def | 1251–1315 | 65 |
| `load_facts_sidecar` | def | 1318–1400 | 83 |
| `compute_version_families` | def | 1403–1432 | 30 |
| `score_gap` | def | 1435–1449 | 15 |
| `rank_gaps` | def | 1452–1456 | 5 |
| `shortlist_size` | def | 1459–1462 | 4 |
| `is_later_or_same_unknown` | def | 1465–1475 | 11 |
| `gap_related` | def | 1478–1481 | 4 |
| `freshness_candidates` | def | 1484–1508 | 25 |
| `load_freshness_cache` | def | 1511–1519 | 9 |
| `save_freshness_cache` | def | 1522–1524 | 3 |
| `gap_scope_keys` | def | 1527–1533 | 7 |
| `load_papers_with_digests` | def | 1536–1545 | 10 |
| `build_gap_pool` | def | 1548–1597 | 50 |
| `Stage2Context` | class | 1600–1767 | 168 |
| `Stage2PackRefineContext` | class | 1770–1847 | 78 |

合计 18 个定义、598 行，位于 runner 的连续区间 1216–1847（前一个定义 `save_projections` 结束于 1213，后一个定义 `stage1_state_path` 起于 1904）。

### 需要注入的 36 个名字

常量与别名（20 个）：`atomic_json@57`（`_contact_io.atomic_json` 的别名）、`fail@65`（`_contact_io.fail` 的别名）、`SCHEMA@220`、`MANAGED_BY@236`、`INPUT_PACK@268`、`FRESHNESS_CACHE@272`、`GAP_SCOPES@282`、`FRESHNESS_SCOPES@283`、`GAP_STATUSES@285`、`AUTHORSHIP_RANK@287`、`FACTS_SCHEMA@299`、`FACTS_KIND@300`、`FACTS_TEXT_FIELDS@304`、`FACTS_LIST_FIELDS@305`、`SHORTLIST_MAX@306`、`SHORTLIST_FLOOR@307`、`EXT_EVIDENCE_RE@318`、`PLACEHOLDER_RE@322`、`SIDECAR_EXTRACTOR_VERSIONS@2012`、`FACTS_GENERATOR_VERSIONS@2013`。

函数（16 个）：`sha256_bytes@332`、`quote_id@348`、`read_json_file@357`、`text_tokens@391`、`title_tokens@402`、`direction_machine_id@424`、`facts_direction_id@447`、`pack_paper_index@468`、`load_input_pack@616`、`paper_digest@960`、`sidecar_sha@979`、`gap_fingerprint@985`、`candidate_fingerprint@995`、`direction_relevant_keys@999`、`pack_direction_relevant_keys@1042`、`direction_fingerprint@1096`。

除 `SIDECAR_EXTRACTOR_VERSIONS@2012` 与 `FACTS_GENERATOR_VERSIONS@2013` 外，其余 34 个名字的定义都在 1216 之前；这两条是 `_stage2_preflight_module` 的常量别名，当前写在 `_stage2_preflight.build(...)`（1969–1982）之后。因此本批要把这两行上移到 `_STAGE2_PREFLIGHT_SPEC.loader.exec_module(...)` 之后、`build()` 调用之前（R4）。

### 使用方（batch 6 之外）

- 四个模块的 `build()` 实参：`_stage2_resolve`（1855–1869，用到 `Stage2Context`）、`_stage2_preflight`（1969–1982，用到 `Stage2Context`、`gap_scope_keys`、`load_freshness_cache`）、`_stage2_finalize`（2615–2654，用到 `Stage2Context`、`Stage2PackRefineContext`、`save_freshness_cache`）、`_stage2_validation`（7261–7300，用到 `Stage2Context`、`Stage2PackRefineContext`）。
- runner 内其它调用点：`migrate_entry_for_professor@7578` 用 `load_sidecar`；`build_direction_pack@2344` 用 `shortlist_size`；`apply_ready_entry@7780/7802/7831` 用 `Stage2Context`、`freshness_candidates`、`save_freshness_cache`；`narrative_scope@2116`、`validate_freshness_results@2022`、`validate_narrative_entry@2128`、`validate_narrative@2212`、`render_analysis_md@2462`、`build_direction_pack@2293` 用 `Stage2Context`。
- 其余 12 个数据函数在本批之外没有直接调用点，只被两个类与上述同名注入使用。

## 设计

新模块 `_stage2_facts.py`（与 runner 同目录），沿用“按路径加载 + 工厂闭包”：

```text
_stage2_facts = _stage2_facts_module.build(
    atomic_json=atomic_json, fail=fail, SCHEMA=SCHEMA, ... 36 个 keyword-only 实参 ...)
sidecar_analysis_matches = _stage2_facts.sidecar_analysis_matches
... 18 个别名 ...
```

- `build()` 的 36 个 keyword-only 参数与上表同名、同集合；`build()` 返回 `types.SimpleNamespace`，成员 18 个。
- 18 个定义原样嵌套在 `build()` 内（只加 4 空格缩进），保持原有先后顺序，便于逐字核对。
- 模块头只保留标准库 `import`：`from __future__ import annotations`、`from datetime import datetime, timedelta, timezone`、`from pathlib import Path`、`from typing import Any`、`import re`、`import types`（`types` 用于 `SimpleNamespace`，`Any` 用于注解；被搬代码不引用 `json`）。
- 加载块放在 `_STAGE2_VALIDATION_*` 之后、`SCHEMA = 1` 之前（`_STAGE2_PREFLIGHT_*` 在 `SCHEMA = 1` 之后，是唯一一组在 SCHEMA 之后的 Stage-2 加载块），写法与 `_STAGE2_VALIDATION_*` 一致（`Path(__file__).with_name(...)` + `spec_from_file_location` + 守卫 + `module_from_spec` + `exec_module`）。
- 绑定块放在被删除区间的起点（`save_projections` 之后）：先 `build()` 调用，再 18 个别名，前后各 2 个空行。
- 两条常量别名（`SIDECAR_EXTRACTOR_VERSIONS`、`FACTS_GENERATOR_VERSIONS`）上移到 preflight 加载块之后；这是本批唯一涉及已有加载区顺序的改动，行为不变（值相同、仍在使用前定义）。

### 取舍

只考虑三个方向：① 模块反向导入 runner：会让新模块依赖 runner 的实现细节，形成双向依赖，且 runner 可能以 `__main__` 方式执行，取不到稳定模块名，否决；② 定义留在 runner、只抽一个轻量包装：没有减小 runner，违背本批目标，否决；③ 沿用既有“按路径加载 + 工厂闭包 + 同名别名”（`_stage2_validation.py` 等五批已在用）：模块不导入 runner、依赖全部显式注入、runner 侧保持同名入口，选中。代价是 36 个参数的 `build()` 调用较长，且两个类的 `__qualname__` 会变成 `build.<locals>.Stage2Context`（见风险 5）。

## 实施步骤

1. 用提取器 `/tmp/pc-stage2-tools/extract_batch_v2.py`（134 行，sha256 `336c58e1937e7e735b1d1678a39630618ae5c6917ecc6be29b93a4b4e6f14b5b`；比第 1–5 批用的 `extract_batch.py` 只多支持顶层类）加 spec `/tmp/pc-stage6/spec-b6.json`（73 行，sha256 `a86dffc021ae8d9e70074f20decd98293efbbe28c4a60ed0a3a877f5a7711ae2`）生成模块与 probe runner。spec 写明：模块名 `_stage2_facts`、18 个定义名（含两个类）、`constants: []`、`load_anchor` = `SCHEMA = 1` 所在行（加载块落在其它 Stage-2 加载块之后）、`bind_before` = `sidecar_analysis_matches`（绑定块落在被删区间起点）、36 个参数名、模块 import（`datetime`、`Path`、`Any`、`re`、`types`）。
2. 把两条常量别名从 2012／2013 上移到 preflight 加载块之后。
3. 插入加载块与绑定块，删除 18 个定义（按 AST 行区间），并把删除后遗留的空行块收敛为 2 个空行——实测删完会留下 37 个连续空行，收敛后 runner 从 8191 行降到 7630 行。
4. 接缝核对：`git diff --ignore-blank-lines -U0` 应只剩 4 个 hunk——
   - `@@ -219,0 +220,12 @@`：加载块 12 行；
   - `@@ -234,0 +247,2 @@`：两条常量别名上移到 preflight 加载块之后；
   - `@@ -1216,632 +1230,59 @@`：18 个定义删除与绑定块新增合并成一个 hunk（绑定块 59 行 = 2 行注释 + `build()` 调用 38 行 + 空行 + 18 个别名）；
   - `@@ -2012,2 +1452,0 @@`：旧位置的两条别名删除。
   不得出现常量值、import、CLI、入口清单或其它顶层定义的改动。
5. 逐字核对：18 个定义在模块内的 AST（忽略 docstring）与基线相同；`inspect.cleandoc` 后 docstring 同文。
6. 运行测试计划（`plan/stage2-facts/test-plan.md`）全部编号。
7. 提交实现与文档，推送 PR；测试结果按编号贴到 PR 评论。

> 实施前已在独立 probe 目录做过一次端到端演练：模块 694 行、runner 7630 行；`--help` 与基线逐字节相同；A/B 98 条 `OK`（T0 3、T1 37、T2 21、T3 37）；T4 13 个方法 `OK`；T5 2 个方法 `OK`；docstring 核对 7/7 同文（5 个多行）、11 个原本没有 docstring。演练产物在 `/tmp/pc-stage6/probe/`，正式提交前按同一 spec 重跑。

## 验证方式

- 结构／AST 等价：用 `/tmp/pc-stage2-tools/compare_stage2_batch_v2.py`（94 行，sha256 `1ba8c0f49346b1fa78c34fbeec4d82cdab206ebef6cbf1b629769f9e5e4346b6`）对 18 个名字做 T0–T3 检查。v1（91 行）只认 `FunctionDef`，遇到本批的两个类会在 T0/T1 失败、T2 取 `base_defs[name]` 抛 `KeyError`；v2 与 v1 只差“顶层定义包含 `ClassDef`”，判据与标签不变。不重写脚本。
- 行为：只跑与本批 18 个名字有直接关系的既有测试方法（清单见测试计划）。
- 仓库既有 CI（4 个 `shards` + 聚合 `test`）照常跑，但属于仓库检查，不是本批必测项。

## 不纳入本批范围

| 未纳入项 | 原因 |
| --- | --- |
| 渲染／校验层（`validate_freshness_results`、`narrative_scope`、`validate_narrative_entry`、`validate_narrative`、`citation_render`、`rendered_markdown_block_lines`、`render_positioning_block`、`redact_item_keys`、`build_direction_pack`、`render_analysis_md`，2022–2610） | 下一批；其中 `render_analysis_md` 依赖第 4 批的 `stage2_require_later_paper_titles`，需要另设计绑定顺序 |
| 方向解析 helper（`profile_fingerprint`、`load_profile_text`、`_direction_slices`、`_cross_group_fresh`、`_parse_direction_id_list`、`_parse_cross_groups`） | 后续批次；与本批无相互依赖 |
| 常量值、CLI、帮助文本、Nix 布局、测试文件 | 本批只做搬移与别名顺序调整 |

## 风险与反例

1. **常量别名上移后与 preflight `build()` 的实参顺序冲突**：反例——若 `FACTS_GENERATOR_VERSIONS` 也是 `_stage2_preflight.build(...)` 的实参，则上移后它仍以同名实参传入，值相同，不受位置影响；实施时必须先确认该调用是否引用这两个名字（实测 30 个实参中没有它们）。
2. **绑定点放在被删区间起点会导致别名早于 `Stage2Context` 的原定义**：反例——若有模块级代码在 1216 之前就用 `Stage2Context`，别名会不存在；实测模块级引用只有四个 `build()` 调用（1855 起），都在绑定块之后。
3. **删除区间不连续**：反例——若 1216–1847 之间夹着不属于本批的定义，整段删除会误删；实测该区间内 18 个定义连续、无其它顶层定义。
4. **docstring 缩进**：搬入 `build()` 后 docstring 续行也要加 4 空格，否则 `inspect.cleandoc` 会不同；用一次性只读脚本核对（同第 5 批做法）。
5. **类的 `__qualname__` 变化**：两个类进入 `build()` 后变成 `_stage2_facts.build.<locals>.Stage2Context`，`repr` 与 traceback 里会显示这个名字。已核对仓库测试没有依赖 `__module__`／`__qualname__`、pickle 或 `inspect.getsource` 的地方，故不阻断；若后续出现依赖，需在模块里改成顶层定义。

## 修订记录

- 第 1 版：首次提交。
- 第 2 版：按计划审核 P4 的两条必改项修正——① “验证方式”改用类感知的 `compare_stage2_batch_v2.py`（94 行，`1ba8c0f4…`），并写明 v1 遇类会失败的原因；② 设计段的模块 import 列表与 spec 对齐（去掉 `json`、补 `types` 与 `__future__`）。同时按非阻断意见补：使用方清单加 `validate_narrative_entry@2128`、加载块位置的准确描述、方案取舍一节、类 `__qualname__` 变化的风险条目。

## 审核状态

- 第 1 版：P1–P3 PASS、P4 NEEDS_MODIFICATION（验证方式仍用 v1 对比脚本；import 列表与 spec 矛盾）。
- 第 2 版：P1–P4 全 PASS，`Plan conclusion: APPROVED`。
