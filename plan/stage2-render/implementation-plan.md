# Stage 2 划分第七批：渲染与校验层（执行计划）

## 版本、来源与状态

- Requirement revision: 第 1 版（2026-10-20 负责人要求：把 `contact_state.py` 收敛为 CLI 分发与确有调用方依赖的兼容入口，每个 stage 的主要逻辑拆成同目录内部模块，按 PR 分批交付）。
- Plan revision: 第 3 版。
- Proposed review status: 待审核。
- Target repository revision: 工作分支 `refactor-stage2-render`，父提交为分支链上一位 `refactor-stage2-context`（#113）的 head `5972905b1aa420f5aebdbd9a06221958fe64a726`（链：#108 → #109 → #110 → #111 → #112 → #113 → 本批）。坐标在链上若发生偏移，按函数名与 AST 重新定位。
- 参考做法：同目录既有的 `_stage2_preflight.py`、`_stage2_resolve.py`、`_stage2_finalize.py`、`_stage2_validation.py`、`_stage2_facts.py` 的“按路径加载 + 工厂闭包 + runner 同名别名”。

## 目标与验收条件

| 编号 | 目标 | 验收条件 |
| --- | --- | --- |
| R1 | 10 个渲染／校验定义离开 runner 顶层 | 10 个名字都不再在 `contact_state.py` 顶层用 `def` 定义；都出现在 `_stage2_render.py` 的 `build()` 内；runner 有对应同名别名 |
| R2 | 搬移不改变逻辑 | 10 个定义体除缩进外逐字相同；自由名字全部来自 `build()` 的 keyword-only 参数（16 个）或同批定义 |
| R3 | 依赖显式注入，模块不反向依赖 runner | `_stage2_render.py` 不 `import contact_state`、不按路径加载 runner、不做动态导入、不碰 `sys.path`／`sys.modules`；16 个依赖全部由 runner 在 `build()` 调用处按同名实参注入 |
| R4 | 解除 `render_analysis_md` 的绑定环 | `stage2_trusted_paper_title`（11 行）与 `stage2_require_later_paper_titles`（22 行）从 `_stage2_finalize.py` 移入 `_stage2_render.py`；两个函数体不变；`_stage2_finalize.build` 由 38 个参数变 40 个（新增这两个）、返回成员由 9 个变 7 个；runner 的两个同名别名改指 `_stage2_render` |
| R5 | 其余行为不变 | 不改常量值、CLI 子命令、帮助文本、Nix 布局与测试文件；`contact_state.py --help` 与父提交逐字节相同 |
| R6 | 接缝可核对 | `git diff --ignore-blank-lines -U0` 只出现“加载块新增”“绑定/别名块”“10 个定义删除”“`_stage2_finalize.py` 的 33 行删除与签名/成员调整”这几类 hunk |

## 现状事实（父提交 `5972905`，runner 7630 行）

| 定义 | 行 | 行数 |
| --- | --- | --- |
| `validate_freshness_results` | 1461–1552 | 92 |
| `narrative_scope` | 1555–1564 | 10 |
| `validate_narrative_entry` | 1567–1648 | 82 |
| `validate_narrative` | 1651–1671 | 21 |
| `citation_render` | 1674–1685 | 12 |
| `rendered_markdown_block_lines` | 1688–1696 | 9 |
| `render_positioning_block` | 1699–1720 | 22 |
| `redact_item_keys` | 1723–1729 | 7 |
| `build_direction_pack` | 1732–1898 | 167 |
| `render_analysis_md` | 1901–2049 | 149 |

合计 10 个定义、571 行，区间连续（区间前面是 preflight 的常量 1453–1458，后一个是 `_stage2_finalize` 的绑定块 2054–2093；绑定块插在 1461）。

### 需要注入的 16 个名字

`fail@65`、`GAP_STATUSES@299`、`PLACEHOLDER_RE@336`、`now_utc@342`、`read_json_file@371`、`truncate@400`、`rel_path@420`、`filename_component@427`、`direction_machine_id@438`、`pack_paper_index@482`、`direction_papers@487`、`direction_relevant_keys@1013`、`direction_provisional_member_keys@1031`、`shortlist_size@1278`、`Stage2Context@1287`、`Stage2PackRefineContext@1288`（后三个由第 6 批的别名提供）。

搬入模块后 `stage2_trusted_paper_title` 与 `stage2_require_later_paper_titles` 也在同一 `build()` 内定义：`render_analysis_md` 调 `stage2_require_later_paper_titles`，后者再调 `stage2_trusted_paper_title`，两条调用都变成同一个 `build()` 里的闭包引用，不再需要跨模块注入。注意 `stage2_require_later_paper_titles` 自己要用 `Stage2PackRefineContext`，所以 16 个参数里必须有它（实施前的 probe 演练就是漏了这个参数才暴露出来）。

### 绑定环（本批要解除）

当前顺序是：`render_analysis_md` 定义在 1901，运行期调用 `stage2_require_later_paper_titles`；该名字的别名在 **2103**；而 `_stage2_finalize.build(...)` 在 **2054–2093** 把 `render_analysis_md` 当实参注入。也就是“`render_analysis_md` 必须在 2054 之前存在，但它依赖的别名到 2103 才出现”。渲染模块的 `build()` 必须放在 1461（早于 2054），所以按原方案搬家会直接 `NameError`。

## 设计

新模块 `_stage2_render.py`，一次 `build()`：

```text
_stage2_render = _stage2_render_module.build(
    fail=fail, GAP_STATUSES=GAP_STATUSES, ... 16 个 keyword-only 实参 ...)
validate_freshness_results = _stage2_render.validate_freshness_results
... 12 个别名（10 个搬移 + 2 个标题 helper）...
```

- `build()` 返回 12 个成员：10 个搬移定义 + `stage2_trusted_paper_title` + `stage2_require_later_paper_titles`。
- `_stage2_finalize.py` 同步调整：删掉这两个嵌套定义（33 行），`build` 新增两个 keyword-only 参数，`SimpleNamespace` 去掉这两项；模块内 `stage2_require_paper_reference_titles` 与 `cmd_stage2_finalize` 改用参数绑定的同名名字，函数体不变。
- runner：`_stage2_render` 加载块放在 `_STAGE2_VALIDATION_*` 之后、`SCHEMA = 1` 之前；绑定块放在被删区间起点（1455 之后）；`_stage2_finalize.build(...)` 增加 `stage2_trusted_paper_title=` 与 `stage2_require_later_paper_titles=` 两个实参；原来 2102／2103 的两行别名删除（由新绑定块的别名取代）。

### 取舍

1. **晚绑定（模块级全局 + `bind()`）**：不需要动已合并的模块，但要在新模块里引入可变模块状态，且 `render_analysis_md` 得改成模块级函数，与五个批次一直用的“工厂闭包”写法不一致，否决。
2. **runner 里加转发函数**：`render_analysis_md` 变成一层转发，签名虽同但对象身份变了，A/B 里“同名别名指向模块函数”的判据要放宽，且以后第 8 批还得再拆一次，否决。
3. **把两个标题 helper 的所有权移到渲染模块**（选中）：33 行代码换一个模块归宿，函数体不变；环从根上消失，绑定顺序变成“渲染模块（1461）→ finalize 模块（2054）”，不再需要任何晚绑定。代价是 `_stage2_finalize.py` 的工厂签名从 38 变 40、成员从 9 变 7，需要在测试计划里单独核对。

## 实施步骤

0. **当前状态**：probe 产物已由实现提交 `ebf2763` 落库（runner 7085 行、`_stage2_finalize.py` 885 行、`_stage2_render.py` 667 行），工作树干净。实施按“把现有产物当作实现、逐项对照 `5972905` 的 blob 复验 R1–R6”执行；若要从零重放，先 `git reset --hard 5972905`（丢弃本批提交），再执行下面 1–5 步。

1. 用 `/tmp/pc-stage2-tools/extract_batch_v2.py`（134 行，sha256 `336c58e1937e7e735b1d1678a39630618ae5c6917ecc6be29b93a4b4e6f14b5b`）加新 spec `/tmp/pc-stage7/spec-b7.json` 生成模块骨架与 probe runner：模块名 `_stage2_render`、10 个函数名、`constants: []`、`load_anchor` = `SCHEMA = 1` 所在行、`bind_before` = `validate_freshness_results`、16 个参数名、模块 import（`datetime`、`Path`、`Any`、`re`、`types`）。
2. 把 `_stage2_finalize.py` 里的两个标题 helper 原样（去掉 4 空格缩进）追加进渲染模块的 `build()`，成员表加两项；再用脚本从 `_stage2_finalize.py` 删除这两个嵌套定义、给 `build` 加两个参数、从 `SimpleNamespace` 去掉两项。
3. 在 runner 里插入加载块与绑定块（含 12 个别名），删除 10 个定义（按 AST 行区间），收敛删除后遗留的空行；删除旧位置的两行标题别名；给 `_stage2_finalize.build(...)` 调用补两个实参。
4. 接缝核对：`git diff --ignore-blank-lines -U0` 应只剩 4 个 hunk——加载块 12 行、10 个定义删除与绑定块（+54 行）、`_stage2_finalize.build(...)` 调用新增 3 行（2 个实参 + 收尾括号）、旧的两行标题别名删除；`_stage2_finalize.py` 自身另有 33 行删除与签名/成员调整。没有常量值、import、CLI、入口清单改动。
5. 逐字核对：10 个定义在渲染模块内的 AST（忽略 docstring）与基线相同；两个标题 helper 在渲染模块内的 AST 与基线 `_stage2_finalize.py` 内的版本相同；`_stage2_finalize.py` 其余 13 个函数的 AST 不变。
6. 运行测试计划全部编号；提交实现与文档，推送分支，开 PR（base 为分支链上一位 `refactor-stage2-context`）。

## 验证方式

- 结构／AST 等价：`/tmp/pc-stage2-tools/compare_stage2_batch_v2.py`（94 行，sha256 `1ba8c0f49346b1fa78c34fbeec4d82cdab206ebef6cbf1b629769f9e5e4346b6`）对 10 个名字做 T0–T3 检查（预期 58 条 `OK`）。**base 目录必须是父提交 `5972905` 的导出**（测试计划第 2 步用 `git archive` 生成）；`/tmp/pc-stage2-tools/base-wt` 是拆分前的旧快照，用它会让 T2 的两条聚合检查失败。
- 两个标题 helper 是“模块到模块”的搬移，不在对比脚本的能力范围内，用测试计划第 2 步的只读 AST 核对：在 `_stage2_finalize.py` 中消失、在 `_stage2_render.py` 中出现且 AST 相同。
- 行为：`stage2-finalize` 与 `stage2-refine-*` 相关的既有测试方法（清单见测试计划）。
- 仓库既有 CI 照常执行，不作为本批必测项。

## 不纳入本批范围

| 未纳入项 | 原因 |
| --- | --- |
| 方向解析 helper（`profile_fingerprint`、`load_profile_text`、`_direction_slices`、`_cross_group_fresh`、`_parse_direction_id_list`、`_parse_cross_groups`） | 第 8 批 |
| `cmd_stage2_plan` 与 Stage 3 主体 | 后续批次 |
| 常量值、CLI、帮助文本、Nix 布局、测试文件 | 本批只做搬移与标题 helper 的所有权调整 |

## 风险与反例

1. **标题 helper 搬走后 `_stage2_finalize.py` 内部还有引用**：实测 Load 点共 5 处——`stage2_trusted_paper_title` 在 267（`stage2_require_paper_reference_titles`）、897（同批搬走的 `stage2_require_later_paper_titles`）、916（成员表）；`stage2_require_later_paper_titles` 在 751（`cmd_stage2_finalize`）、917（成员表）。除同批搬走的那处外，其余都要靠新参数提供；漏一个就会在 `stage2-finalize` 上报 `NameError`。
2. **runner 里还有别处直接用这两个名字**：反例——除 `_stage2_finalize.build`／`_stage2_validation.build` 的实参外，若还有顶层函数直接调用，别名必须早于它们的运行期调用；绑定块插在 1461，所有调用点都在其后。
3. **`_stage2_finalize.py` 的签名变化漏改调用方**：反例——runner 只在一处调用 `_stage2_finalize.build`，漏传新参数会在导入期 `TypeError`；T0 的 `--help` 与工厂契约检查会直接暴露。
4. **delete/插入行区间不连续**：反例——1461–2049 之间若夹着不属于本批的定义，整段删除会误删；实施前用 AST 确认区间内恰好 10 个定义。
5. **docstring 缩进**：搬入 `build()` 后 docstring 续行加 4 空格，否则 `inspect.cleandoc` 不同；用只读脚本核对。

## 实施前演练（probe）

按同一 spec 演练并先生成了 probe 产物，随后把产物落到工作树逐项复验（对照 `5972905` 的 blob）：模块 667 行、runner 7086 行；`--help` 与父提交逐字节相同；A/B 58 条 `OK`（T0 3、T1 21、T2 13、T3 21）；两个标题 helper 的 AST 跨模块相同；T4 7 个方法 `OK`；T5 2 个方法 `OK`。演练第一次跑时漏了 `Stage2PackRefineContext` 参数，`stage2-finalize` 直接 `NameError`，因此本计划已把它写进 16 个注入名。

## 修订记录

- 第 1 版：首次提交。
- 第 2 版：按实施前演练修正——注入名由 15 个改为 16 个（补 `Stage2PackRefineContext`，`stage2_require_later_paper_titles` 需要它），并把接缝判据写成实测的 4 个 hunk；对照基准改为分支链上一位 `refactor-stage2-context`（#113）的 head `5972905`。

## 审核状态

- 第 1 版：待计划审核。
- 第 2 版：P1／P4 NEEDS_MODIFICATION（初始状态与工作树不符；现状事实标题仍写 `3da3d4a`）。
- 第 3 版：待复核——① 新增第 0 步写明 probe 产物已在工作树、按“现有产物即实现”复验，并给出从零重放的回退命令；② 现状事实标题改为 `5972905`；③ 按实测改注入名位置（`Stage2PackRefineContext@1288`）、绑定环描述、区间前后文、Load 点清单、compare 的 base 目录要求，probe 数字改为 667／7086。
