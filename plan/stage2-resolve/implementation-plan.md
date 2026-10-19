# Stage 2 划分第二批：把 resolve 计划层抽成内部模块（执行计划）

## 版本、来源与状态

- 需求来源：负责人 2026-10-20 的指示：

  > 你把stage 2 拆分完后，后面其他的stage也要继续拆，目标是contact_state.py这个1w多行的文件，应该变为一个CLI 分发和确有调用方依赖的兼容入口，然后每个stage的主要逻辑应该拆分为单独的模块，就像前面做的各种拆分一样，contact_state.py应当大幅瘦身

  以及同日的 Stage 2 划分指示（“基于当前主分支对 stage2 进行划分”）。本批是该划分的第 2 批。
- Requirement revision: 第 1 版（2026-10-20）。
- Canonical Plan revision: 第 1 版。
- Target repository revision: `d5a4f751fb80de4819d4a1de3ee829db52cea6fc`（当前 `main`）。本批工作分支 `refactor-stage2-resolve` 从该提交拉出。第 1 批（`refactor-stage2-split`，PR #108）尚未合并；两批改动的行区间不重叠，本批按独立分支交付，合并顺序不构成前置。
- Relevant upstream/runtime revision: N/A；不涉及外部仓库、代理入口、安装布局或 CLI 变化。
- Proposed review status: pending（P1–P4 结论只由正式 Review record 给出）。
- 唯一规范来源：本文件。本文件只定义实施方案，不声明计划审核、测试审核或合并关口已经通过。

## 所属划分（第 2 / 6 批）

Stage 2 按 6 批交付，第 1 批（预检、身份与 `stage2-preflight`／`stage2-plan` 命令层，`_stage2_preflight.py`）已在 PR #108 提交审核；本批是第 2 批：

| 批次 | 新模块 | 内容 |
| --- | --- | --- |
| 1（PR #108） | `_stage2_preflight.py` | 预检输入与身份、artifact 守卫、pack 指纹、validator 接受判定、preflight/plan 命令 |
| 2（本批） | `_stage2_resolve.py` | 候选识别、resolve 证据与模型输入、`stage2-resolve-plan` 命令、运行指纹 |
| 3 | 追加到 `_stage2_resolve.py` | resolve 结果校验、证据证明、`stage2-resolve-finalize`／`stage2-resolve-accept` |
| 4 | `_stage2_finalize.py` | finalize 预检漂移、渲染状态、`stage2-finalize` |
| 5 | `_stage2_validation.py` | 校验报告、后续论文、`stage2-refine-*` 与 `stage2-record-validation` |
| 6 | `_stage2_context.py` | 两个上下文类与 facts／pack 渲染闭包 |

本批边界：只搬 resolve 的“计划”一侧——从候选识别到 `resolve plan` 输出 job 与运行指纹。提交侧的校验（`validate_resolve_results`、`_load_existing_resolved`、`_facts_preflight_proof`、`_sidecar_preflight_proof`、`_check_resolved_proof_binding`）与 `resolve finalize/accept` 命令留在第 3 批。

## 正式需求与范围

- **R1 划分**：把本批 16 个函数与 7 个常量原样移入新内部模块 `_stage2_resolve.py`，`contact_state.py` 保留同名同签名的模块级入口。
- **R2 行为不变**：候选识别结果、resolve 证据与模型输入、`stage2-resolve-plan` 的 stdout JSON、失败原因码与退出码逐字节不变；不改变阈值、排序、指纹或 schema。
- **R3 依赖显式**：模块不 import runner、不改 `sys.path`、不注册 `sys.modules`；所需 runner 名字全部以显式参数注入，模块内不出现第二份实现。
- **R4 加载方式**：沿用第 1 批与仓库既有内部模块做法（`Path(__file__).with_name(...)` + `importlib.util.spec_from_file_location` + `module_from_spec` + `exec_module`）。
- **R5 兼容面**：`contact_state.<被搬函数>`、`contact_state.AUTHORSHIP_RANK` 等模块级名字、CLI 子命令与测试入口（含 `test_stage2_resolved_direction_regressions.py` 的四个直接调用）都不改。

**非目标**：不改任何业务逻辑、阈值、指纹版本含义、schema、输出字段或排序；不改 resolve 提交侧与 finalize/refine/校验（第 3–5 批）；不改 `Stage2Context`（第 6 批）；不改测试断言与测试名称；不改 CLI、七个薄入口与 Nix 布局；不修本块内既有死代码或风格问题。

## 依据与关键事实

审核依据为项目 `PROJECT_CONSENSUS.md` 与 `Plan Reviewer Rule.md`；测试设计另按 `Test Engineer Rule.md` 审核。以下行号均指 `d5a4f75` 的 `scripts/contact_state.py`（该文件与第 1 批基线 `b5621db` 相同）。

| 决定 | 关键事实 | 来源（目标修订） |
| --- | --- | --- |
| 本批 16 个函数 | 候选识别：`_compute_paper_direction_affinity` 1824-1906、`_detect_candidates_for_addition` 1909-1982、`_detect_candidates_for_removal` 1985-2057、`_detect_split_candidates` 2060-2120、`_profile_topic_tokens` 2123-2138、`_direction_fulltext_terms` 2153-2164、`_merge_fulltext_basis` 2167-2191、`_authoritative_merge_basis` 2194-2218、`_direction_has_valid_fulltext` 2221-2229、`_detect_merge_candidates` 2232-2289、`_canonical_directory` 2292-2297；resolve 计划：`stage2_resolve_run_id` 2300-2316、`cmd_stage2_resolve_plan` 2319-2467、`_resolve_evidence` 2470-2489、`_build_resolve_model_input` 2492-2575、`_current_resolve_fingerprint` 2581-2594 | `scripts/contact_state.py` |
| 7 个常量只被本批使用 | `MERGE_MIN_SHARED` 2141、`MERGE_MIN_FACTS_PAPERS` 2142、`MERGE_MIN_SHARED_TERMS` 2143、`MERGE_TOPIC_OVERLAP` 2144、`MERGE_VALIDATION_MIN_FACTS_PAPERS` 2149、`MERGE_VALIDATION_MIN_SHARED_TERMS` 2150（含 2145-2148 的说明注释）、`RESOLVE_INPUT_FINGERPRINT_VERSION` 2578 | 全仓引用检索：这些名字的读取只在本批函数内 |
| `AUTHORSHIP_RANK` 不搬 | 定义在 240，除本批 1882 外还被 `score_gap` 1415 使用，是跨块共享常量 | 同上 |
| 组外调用点 | `validate_resolve_results`（第 3 批）2825/2840 调 `_authoritative_merge_basis`／`_direction_has_valid_fulltext`，2655/2659 调 `_resolve_evidence`／`_current_resolve_fingerprint`；`cmd_stage2_resolve_finalize` 3024 调 `stage2_resolve_run_id`、3004/3005 调证据/指纹；`cmd_stage2_resolve_accept` 3162/3168 调证据/指纹；第 1 批模块的 `stage2_resolution_evidence_guards` 通过 runner 别名使用 `_resolve_evidence`（注入点在 3594 对应行）；`cmd_stage2_finalize` 4987/4993 调证据/指纹；`stage2_pack_matches_facts` 10665 调 `_canonical_directory`；`build_parser` 11592 引用 `cmd_stage2_resolve_plan` | 对 AST 的组外引用统计 |
| 测试直接调用四个名字 | `test_stage2_resolved_direction_regressions.py` 91 调 `_detect_candidates_for_addition`、122 调 `_detect_merge_candidates`、152 调 `_resolve_evidence`、153 调 `_current_resolve_fingerprint`（均经 `contact_state.`） | 上述测试文件 |
| 没有 import 期引用 | 16 个函数与 7 个常量没有被模块级语句、默认参数、装饰器、类体默认值引用 | 对顶层语句与默认参数的 AST 检索（证据见测试记录） |
| 绑定位置 | 最晚依赖是 `_facts_preflight_proof`（2917），其余依赖更早：`AUTHORSHIP_RANK` 240、`direction_candidate_keys` 1035、`selected_candidate_union` 1050、`Stage2Context` 1574、`_load_existing_resolved` 2886；为保持提交侧 helper 连续，工厂调用取在 `_check_resolved_proof_binding`（2946-2966）之后、`cmd_stage2_resolve_finalize`（2969）之前 | `scripts/contact_state.py` |
| 内部互调 20 处 | 16 个函数之间的调用共 20 处，均由工厂闭包直接解析，不需要在每个调用点补注入 | 对 AST 的组内调用统计 |
| 相邻模块既有加载做法 | `_contact_io` 48-54、`_contact_evidence` 73-80、`_stage3_handoff` 158-164、第 1 批 `_stage2_preflight` 的加载/绑定 | `scripts/contact_state.py` |
| 测试夹具按通配复制内部模块 | 两个复制 runner 的夹具用 `sorted(RUNNER.parent.glob("_*.py"))` 复制相邻模块，新模块自动被带上 | `tests/test_stage5_immutable.py:220`、`tests/test_stage5_dualtarget_contract.py:331` |
| Nix 按整树复制 | runtime 派生 `cp -R .apm/skills/professor-contact/.` 后只改七个入口的 shebang；`entryNames` 不变 | `nix/contact.nix:124-152` |
| 第 1 批的注入约定位 | 第 1 批模块 `_stage2_preflight.py` 把 `_resolve_evidence` 作为 build 参数注入（`stage2_resolution_evidence_guards` 使用）；本批把 `_resolve_evidence` 移到 `_stage2_resolve.py` 后，runner 的别名仍在第 1 批 build 调用之前定义（本批绑定在 2967，第 1 批绑定在 3255），所以第 1 批仍拿到同一对象；两批合并后不需要改第 1 批的 build 调用 | 第 1 批 PR #108 的装配；本批绑定位置 |
| 测试不重绑本批依赖 | 仓内 `mock.patch`／`patch.object` 只碰 `contact_state.os` 属性；没有对 `fail`、`emit`、`sha256_obj`、`_resolve_evidence` 等的赋值或 patch | 对 `tests/` 的检索 |

## 方案

### 因果链

需求（Stage 2 继续按边界拆分，runner 瘦身）→ 现行机制（resolve 计划层的 16 个函数与 7 个阈值/版本常量散在 runner 1824-2594，依赖上下文类、候选并集、facts 预检证明、错误通道与 sha）→ 变更点（把这一组原样移入同目录内部模块，模块用一次工厂接收 runner 的名字；runner 在提交侧 helper 之后建立模块命名空间并保留同名入口）→ 行为变化（候选识别、job 输出、指纹与失败路径不变；runner 少约 730 行，多一个内部模块与一段绑定代码）→ 满足需求。

### 选定设计

**新模块 `scripts/_stage2_resolve.py`**：

- 文件头：`from __future__ import annotations`、`from pathlib import Path`、`import types`（本批函数不需要 `json`／`re`；以搬移后的自由名清单为准）。
- 模块级定义 7 个常量（值逐字照搬，含 `MERGE_VALIDATION_*` 前的说明注释）。
- 模块主体为工厂 `build(...)`，参数为本批需要的 runner 名字，名字与函数体里的旧自由名逐字一致：

  ```python
  def build(*, AUTHORSHIP_RANK, Stage2Context, _facts_preflight_proof,
            _load_existing_resolved, direction_candidate_keys,
            selected_candidate_union, emit, fail, filename_component,
            sha256_obj, truncate):
      # 16 个函数逐个原样搬入（只增加缩进；函数体不改）
      ...
      return types.SimpleNamespace(_compute_paper_direction_affinity=..., ...)
  ```

  参数名与旧自由名一致，因此 16 个函数体逐字不变；内部互调由闭包解析，不需要逐调用点补参。

**runner 侧加载与绑定**：

- 顶部（与既有内部模块并列）按路径加载 `_stage2_resolve.py`，得到 `_stage2_resolve_module`。
- 在 `_check_resolved_proof_binding`（2966）之后、`cmd_stage2_resolve_finalize`（2969）之前调用一次工厂：

  ```python
  _stage2_resolve = _stage2_resolve_module.build(
      AUTHORSHIP_RANK=AUTHORSHIP_RANK, Stage2Context=Stage2Context,
      _facts_preflight_proof=_facts_preflight_proof,
      _load_existing_resolved=_load_existing_resolved,
      direction_candidate_keys=direction_candidate_keys,
      selected_candidate_union=selected_candidate_union, emit=emit, fail=fail,
      filename_component=filename_component, sha256_obj=sha256_obj, truncate=truncate)
  ```

- 绑定后建立 16 个同名别名与 7 个常量别名；删除原位 1824-2594 的 16 个定义（常量与函数之间不动的代码保持原位）。
- runner 里其它调用点（2825、2840、2655、2659、3004、3005、3024、3162、3168、3594 对应注入、4987、4993、10665、11592）一行不改。

**为什么沿用工厂闭包**：与第 1 批相同——16 个函数、11 个依赖、20 处内部互调；闭包让函数体逐字不变、缺依赖在导入期 `TypeError`、内部互调不需要人工补参。两批使用同一种装配方式，后续批次可直接复制模式。

**替代方向与取舍**：

| 方向 | 不采用的原因 |
| --- | --- |
| 逐函数关键字注入 | 20 处内部调用都要补参，编辑面更大且漏传只在运行到该分支时暴露 |
| 模块 `import contact_state` | 循环导入；测试按文件路径加载 runner |
| 加载后给模块属性赋值 | 隐式全局状态，与既有内部模块的显式注入约定冲突 |
| 把提交侧 helper 一起搬 | 提交侧的校验、证明与命令属第 3 批，失败方式不同，混做会扩大审核面 |
| 把 `_canonical_directory` 留在 runner | 它只被本批与 `stage2_pack_matches_facts` 使用；本批搬走后由 runner 别名供第 5 批使用，避免在模块里留一个未使用的 helper |
| 把 `AUTHORSHIP_RANK` 搬进模块 | 它在 `score_gap` 里也被使用，是跨块共享常量 |

### 冻结的契约

- 16 个函数的名字、参数、默认值、返回结构、排序与失败原因码不变；runner 入口是同一个函数对象，不是包装函数。
- 7 个常量的类型与值不变（含 `RESOLVE_INPUT_FINGERPRINT_VERSION = 4` 的语义）。
- 错误通道仍只有 runner 的一份；模块不 import `_contact_io`，不新建业务通道。
- `stage2-resolve-plan` 的 stdout JSON 字段、顺序与值不变。
- 模块是内部辅助模块：不进入口清单，不改 `entryNames`。

## 影响

- **intended_change**：16 个函数与 7 个常量移入 `_stage2_resolve.py`；runner 增加加载、一次工厂绑定、16 个函数别名与 7 个常量别名。
- **preserved_behavior**：`stage2-resolve-plan` 的 job 输出（含 `model_input`、`result_schema`、`write_needed`）与失败路径；候选识别与 merge 阈值；resolve 证据与指纹；`Stage2Context` 的行为；所有既有调用点与测试入口；复制夹具与 Nix 安装树。
- **approved_behavior_change**：无。
- **prohibited_side_effect**：修改任何阈值、排序、指纹、schema、输出字段；修改测试断言；复制 runner helper 的实现；新建第二错误通道；改 CLI、入口清单或安装布局；顺手搬提交侧/上下文类；改 `sys.path` 或注册 `sys.modules`。
- **unresolved impact**：
  1. 与第 1 批相同的函数元数据变化（`__module__`／`__qualname__`、`pickle` 按引用、`get_type_hints` 字符串注解）——仓内无消费者。
  2. 第 3 批把 `_facts_preflight_proof`／`_load_existing_resolved` 移出 runner 时，必须同步更新本批工厂的注入点（否则闭包仍持有旧的函数对象）；排序依赖写入第 3 批计划即可。
  3. 第 1 批若先合并、第 2 批后合并，本批的 runner 别名定义位置（2967）必须仍在第 1 批 build 调用（3255）之前；按当前行号成立，合并后由测试与 AST 检查复核。
  4. scripts 目录多一个内部模块，与既有内部模块同性质。
  5. 第 6 批搬 `Stage2Context` 时必须同步更新本批工厂的 `Stage2Context=` 注入点（本批把它作为参数注入）；排序依赖写入第 6 批计划即可，不影响本批。

## 关键安全条件与反例

必须一直成立的条件：

1. 16 个函数的代码 AST 与搬移前逐字等价；只允许缩进与 docstring 续行缩进。
2. 7 个常量值不变，只定义一次（模块），runner 只别名。
3. runner 无论直接执行还是按路径加载都能加载模块，工厂只调用一次，且在所有依赖定义之后。
4. `contact_state.<16 个名字>`、`contact_state.<7 个常量>` 与四个测试直接调用保持可用；签名不变。
5. 错误通道仍只有一份；模块不导入 runner、不新建通道。
6. `stage2-resolve-plan` 的 stdout 与失败路径不变。
7. 两个复制夹具自动带上新模块。

代表性反例：

- 工厂在 `_facts_preflight_proof` 定义之前调用 → 导入期 `NameError`；绑定位置固定在 2966 之后，由完整套件覆盖。
- 某个函数体引用了未列入工厂参数的名字（例如 `direction_candidate_keys` 只在两处用到）→ 调用时 `NameError`；由完整套件与自由名清单覆盖。
- 把 `RESOLVE_INPUT_FINGERPRINT_VERSION` 留在 runner 又在模块定义 → 两处可能漂移；本方案要求只在模块定义、runner 别名。
- 把 `_canonical_directory` 留在 runner 却忘记注入 → `stage2_pack_matches_facts` 仍可用、但模块内调用失败；本方案把它一起搬并保留别名。
- 第 3 批搬走 `_facts_preflight_proof` 后忘记更新本批 build 注入 → 本批闭包持有旧对象；写入第 3 批计划与合并检查。
- 测试在导入后重绑 runner 名字 → 闭包仍用旧对象；仓内没有这种重绑，后续测试设计应避免（与第 1 批同一约束）。

## 实施位置与顺序

1. **计划审核**：本文件取得 `Plan conclusion: APPROVED`。
2. **本地执行代理**：新建模块；runner 顶部加载、2967 处绑定与别名；删除原位 16 个定义与 7 个常量定义；AST/常量/调用点对比。
3. **测试计划工程师**：`plan/stage2-resolve/test-plan.md`。
4. **本地测试工程师**：执行并写 `plan/stage2-resolve/test-execution-<date>.md`。
5. **实现符合性审核**（M2）与 **合并审核**（M3）按 `Merge Reviewer Rule.md` 另做。

## 记录

- 计划审核：待补。
- 测试计划与执行：待补。
- AST／常量／调用点对比证据：放仓库外 `/tmp`，记录里写明路径与摘要。
