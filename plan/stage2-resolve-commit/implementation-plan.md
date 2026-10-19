# Stage 2 划分第三批：把 resolve 提交层追加进同一模块（执行计划）

## 版本、来源与状态

- 需求来源：负责人 2026-10-20 的指示（Stage 2 划分；“contact_state.py 应收敛为 CLI 分发与确有调用方依赖的兼容入口，每个 stage 主体逻辑拆为单独模块”）。
- Requirement revision: 第 1 版。Canonical Plan revision: 第 2 版（第 1 版审核意见已并入，见修订记录）。
- Target repository revision: 引用基线 `d5a4f751fb80de4819d4a1de3ee829db52cea6fc`；当前 `main` 已前进到 `0f89ebd`（#105，只改 Stage 5 的 `cmd_stage5_list_inputs` 与帮助文本，与本批区域不重叠），合并前按新基线重放。本批**堆叠**在 `refactor-stage2-resolve`（第 2 批，PR #109）之上：实现时把 `refactor-stage2-resolve-commit` 变基到第 2 批的最新提交，形成 stacked PR；合并顺序为先第 2 批、后本批。
- Relevant upstream/runtime revision: N/A。
- Proposed review status: **APPROVED**（`Plan conclusion: APPROVED`；2026-10-20 计划审核，P1–P4 全 PASS，无 blocker；第 2 版修正见修订记录）。
- 唯一规范来源：本文件。

## 所属划分

Stage 2 分 6 批；本批是第 3 批，与第 2 批共用模块 `_stage2_resolve.py`：第 2 批建立该模块（16 函数 + 7 常量 + 一次 `build()`），本批把 resolve 提交层的 7 个函数追加进同一模块，并扩展同一个 `build()` 的参数；runner 仍然只有一次 `_stage2_resolve = ...build(...)` 调用。

## 正式需求与范围

- **R1 追加**：把本批 7 个函数原样追加到 `_stage2_resolve.py` 的 `build()` 作用域；`contact_state.py` 保留同名同签名入口。
- **R2 行为不变**：`stage2-resolve-finalize`／`stage2-resolve-accept` 的 stdout、写入文件、失败原因码与退出码不变；`validate_resolve_results` 的校验规则与排序不变。
- **R3 依赖显式**：模块不 import runner、不改 `sys.path`、不注册 `sys.modules`；新增的 runner 依赖全部加入 `build()` 参数，stdlib 依赖由模块头导入（本批新增 `import json`），模块内不出现第二份实现。
- **R4 加载方式**：沿用第 2 批的按路径加载；不新增加载块。
- **R5 兼容面**：7 个函数、`contact_state.validate_resolve_results` 等入口、`build_parser` 11601/11608、测试直接调用不改。

**非目标**：不改业务逻辑、阈值、schema、输出或排序；不搬 `Stage2Context`（第 6 批）、`stage2-finalize` 层（第 4 批）、校验/refine（第 5 批）；不改第 2 批已搬的 16 个函数体。

## 依据与关键事实

行号分两套：**参考坐标**指 `d5a4f75`；**堆叠坐标**指第 2 批实现提交（`refactor-stage2-resolve` 的 `2ecdc9c`）。实现必须按函数名/AST 定位，不得套用参考行号去删改堆叠文件——第 2 批把 16 个函数移走后，本批 7 个函数在堆叠文件里位于 1840-2480（`validate_resolve_results` 1840-2126、`_load_existing_resolved` 2129-2157、`_facts_preflight_proof` 2160-2176、`_sidecar_preflight_proof` 2179-2186、`_check_resolved_proof_binding` 2189-2209、`cmd_stage2_resolve_finalize` 2256-2408、`cmd_stage2_resolve_accept` 2411-2480），并且被 2212-2253 的 build/别名/常量块分成两段。

| 决定 | 关键事实 | 来源 |
| --- | --- | --- |
| 本批 7 个函数 | 参考坐标（`d5a4f75`）：`validate_resolve_results` 2597-2883(287)、`_load_existing_resolved` 2886-2914(29)、`_facts_preflight_proof` 2917-2933(17)、`_sidecar_preflight_proof` 2936-2943(8)、`_check_resolved_proof_binding` 2946-2966(21)、`cmd_stage2_resolve_finalize` 2969-3121(153)、`cmd_stage2_resolve_accept` 3124-3193(70)；合计 **585 行**；堆叠坐标见上 | AST 实测 |
| 无新常量 | 本批不引入常量；`RESOLVED_DIRECTION_SCHEMA`(220) 被块外使用，注入；第 2 批的 7 个常量不变 | 全仓引用统计 |
| 新增注入参数（参考坐标 `d5a4f75`） | `atomic_json`(57)、`RESOLVED_DIRECTION_SCHEMA`(220)、`now_utc`(302)、`read_json_file`(331)、`direction_provisional_member_keys`(991)；`Stage2Context`／`emit`／`fail`／`sha256_obj`／`filename_component` 第 2 批已注入 | 自由名闭包 |
| 从注入改为同模块兄弟 | `_facts_preflight_proof`、`_load_existing_resolved` 在本批搬入模块；第 2 批 `build()` 里这两个参数改为同作用域函数（不再注入），第 2 批的 `stage2_resolve_run_id`、`cmd_stage2_resolve_plan` 直接调用同模块函数 | 第 2 批模块与自由名分析 |
| 内部互调 6 处 | 7 个函数之间 6 处调用；另有对第 2 批函数（`_authoritative_merge_basis`、`_direction_has_valid_fulltext`、`_resolve_evidence`、`_current_resolve_fingerprint`、`stage2_resolve_run_id`）的调用，全部是同作用域兄弟 | AST 统计 |
| 组外调用点（参考坐标 `d5a4f75`） | `stage2_resolve_run_id` 2309 用 `_facts_preflight_proof`、`cmd_stage2_resolve_plan` 2360 用 `_load_existing_resolved`、2445 用 `_facts_preflight_proof`（这些在第 2 批模块内）；`cmd_stage2_finalize` 5019/5020/5023 用 `_facts_preflight_proof`／`_sidecar_preflight_proof`；`build_parser` 11601/11608 用两个命令 | AST 统计；均运行期解析 |
| 没有 import 期引用 | 7 个函数与相关常量没有出现在模块级语句、默认参数、装饰器或类体 | AST 检索 |
| 绑定位置不变 | 第 2 批的 `build()` 调用在堆叠文件的 2217 行；本批把 `_facts_preflight_proof`／`_load_existing_resolved` 搬进模块后，新增参数的最晚定义是 `direction_provisional_member_keys`（参考 991／堆叠 1005），早于 2217；因此**不移动**绑定位置，只扩展实参 | 第 2 批实现提交实测 |
| 堆叠重放 | 第 2 批分支未合并；本批实现时以其实现提交 `2ecdc9c` 为基线：在现有 `_stage2_resolve.py` 的 16 个函数之后**追加** 7 个函数（不重建第 2 批的常量与注释），文件头补 `import json`；runner 仍只有 2217 行处一次 `build()` 调用，扩展实参并新增 7 个别名；PR 说明依赖第 2 批 | 第 2 批 PR #109 |
| 加载与复制 | 第 2 批已加入 `_stage2_resolve.py`；两个夹具 `glob("_*.py")` 自动带上；Nix 整树复制不变 | 第 2 批计划、仓库文件 |

## 方案

### 因果链

需求（resolve 提交层也拆出）→ 现行机制（7 个函数在 2597-3193，依赖第 2 批已搬的候选识别/证据/指纹与 runner 的写入、schema、时间、读文件 helper）→ 变更点（把 7 个函数追加进 `_stage2_resolve.py`，扩展同一个 `build()` 的参数；runner 删除原位定义并加 7 个别名）→ 行为变化（finalize/accept 输出与校验不变；runner 少 585 行，模块增加到 23 个函数）→ 满足需求。

### 选定设计

- `_stage2_resolve.py`：文件头新增 `import json`（`_load_existing_resolved` 使用 `json.loads`／`json.JSONDecodeError`，属 stdlib，不作为 build 参数）；在第 2 批的 16 个函数之后追加 7 个函数（原样，只增加缩进）；`build()` 参数新增 `atomic_json`、`RESOLVED_DIRECTION_SCHEMA`、`now_utc`、`read_json_file`、`direction_provisional_member_keys`，并移除 `_facts_preflight_proof`、`_load_existing_resolved` 两个注入参数（改为同模块函数），参数总数由 11 变为 14；返回的命名空间增加 7 个名字。
- runner：把现有 `build()` 调用的实参按上述增减；在别名块追加 7 行；删除原位 7 个定义。加载块、绑定位置、其它调用点不改。
- `Stage2Context` 留在 runner，继续以注入值使用。

**替代方向**：第 3 批另建 `_stage2_resolve_commit.py`（多一个模块与一次绑定，且要把第 2 批函数再注入一遍）；逐函数关键字注入（6 处内部互调要补参）；模块 import runner（循环导入）。

### 冻结契约

- 7 个函数的名字、参数、默认值、返回结构、写入顺序与失败原因码不变；别名是同一函数对象。
- 第 2 批的 16 个函数与 7 个常量不变。
- `build()` 只调用一次；模块仍按路径加载。
- CLI `stage2-resolve-finalize`／`stage2-resolve-accept` 与入口清单不变。

## 影响

- **intended_change**：7 个函数追加进 `_stage2_resolve.py`；`build()` 参数增减；runner 删除 7 个定义并加 7 个别名。
- **preserved_behavior**：finalize/accept 的 JSON、写入与顺序、失败路径；`validate_resolve_results` 的校验与排序；第 2 批的计划层行为；所有调用点与夹具。
- **approved_behavior_change**：无。
- **prohibited_side_effect**：改逻辑/常量/输出/顺序；改第 2 批函数体；改测试；复制 helper 实现；新建第二错误通道；搬类/finalize/校验；改 CLI/入口/Nix。
- **unresolved impact**：与第 1/2 批相同的函数元数据变化；第 6 批搬 `Stage2Context` 时须更新本模块 `build()` 的 `Stage2Context=` 实参；本批依赖第 2 批先合并（若不合并，本批 PR 不能单独合入）。

## 关键安全条件与反例

1. 7 个函数的代码 AST 与搬移前逐字等价（只允许缩进与 docstring 续行缩进）。
2. `build()` 只调用一次；build 参数覆盖来自 runner 的全部依赖，stdlib 依赖由模块头导入（本批新增 `import json`）；缺关键字参数在导入期 `TypeError`。
3. `contact_state.<7 个名字>` 与签名不变；`cmd_stage2_finalize` 的 5019/5020/5023 调用点不改。
4. 第 2 批的 16 个函数与 7 个常量行为不变。
5. 错误通道只有一份。
6. 两个命令的 stdout/写入不变。
7. 堆叠重放后 patch 只含本批增量。

反例：把 `_facts_preflight_proof` 继续作为注入参数 → runner 里没有该定义了，导入期 `NameError`；忘记从 build 参数中移除 `_facts_preflight_proof`／`_load_existing_resolved` → runner 实参少一个位置，导入期 `TypeError`；漏加 `import json` → 存在 `_resolved_directions.json` 时运行期 `NameError`；把 `RESOLVED_DIRECTION_SCHEMA` 复制进模块 → 与 runner 常量漂移；堆叠基线不是第 2 批最新 → PR 含第 2 批重复改动。

## 实施位置与顺序

1. 计划审核取得 `Plan conclusion: APPROVED`。
2. 等第 2 批实现提交（PR #109 的 `2ecdc9c`；分支 tip `630aec3` 只有文档提交）可用；把本工作树变基到 `2ecdc9c`。
3. 在堆叠基线上按函数名定位：删除 runner 里 7 个定义、扩展 2217 行处的 `build()` 实参、加 7 个别名；在模块尾部追加 7 个函数并在文件头补 `import json`；AST/常量/调用点对比。
4. 测试计划（`plan/stage2-resolve-commit/test-plan.md`）与执行记录。
5. M2 与合并审核另做；PR 基于 `refactor-stage2-resolve` 分支。

## 修订记录

- 第 1 版：首次提交计划审核。
- 第 2 版：按计划审核修正——① 补 `import json`（B1）；② 区分参考坐标与堆叠坐标，明确按函数名/AST 定位、绑定在堆叠文件 2217（B2）；③ 非目标改为 `stage2-finalize`；④ 反例改为漏移除 build 参数与漏加 `import json`；⑤ 追加而非重建模块；⑥ 基线指针注明当前 main `0f89ebd`。

## 审核状态

- 计划审核：`Plan conclusion: APPROVED`（2026-10-20；P1–P4 全 PASS，`Required modifications: N/A`）。第 1 版 B1（缺 `import json`）与 B2（堆叠坐标）已在第 2 版关闭；P2/P3/P4 复用第 1 版 PASS。
- 测试计划与执行：待补。

## 记录

- 对比证据放 `/tmp`；测试计划与执行记录在 `plan/stage2-resolve-commit/` 下。
