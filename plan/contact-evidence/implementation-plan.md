# 边界三：把联系证据的上游定位、检查与重建移入内部模块（执行计划）

## 版本、来源与状态

- 需求来源：负责人 2026-10-18 三批要求中的“其余边界”原文：

  > 共享错误通道、事务／回滚、Stage3 提交与校验交接、Stage4/5 证据处理：先按常规审核。移动时可能改变共享状态、异常类型或路径定位，不能仅保留旧函数名就认定等价。

- Requirement revision: 第 1 版（边界三：Stage4/5 证据处理，本批只做“上游证据定位、检查与重建”这一半）。
- Canonical Plan revision: 第 3 版。
- Target repository revision: `2117fc6a1607a22aa9e723002b4a78625733b7b1`（分支 `refactor/stage3-handoff`，已含批次二/三与边界一/二）。
- Implementation sequencing prerequisite: PR #97 已合并；#98、#99、#100 尚未合并，本批堆叠在 #100 之上，合并顺序 #97（已合并）→ #98 → #99 → #100 → 本批。
- Relevant upstream/runtime revision: `professor-research` 的 `professor-collector/scripts/contact_evidence.py` 不在本仓；本批只移动**调用侧**代码，调用方式（传 `program_root`、`--check` 与否、超时）保持不变。
- Proposed review status: **APPROVED**（`Plan conclusion: APPROVED`，P1–P4 全 PASS；独立计划审核于 2026-10-18/19 给出）。
- 唯一规范来源：本文件。

## 正式需求与范围

- **R1 抽上游证据层**：把联系证据的**上游定位、检查与重建**移入一个内部模块：`load_contact_evidence`、`upstream_check_script`、`run_contact_evidence_check`、`run_contact_evidence_rebuild`、`run_upstream_check_argv`、`professor_source_state`、`source_state_needs_rebuild`、`resolve_contact_evidence` 共 8 个函数，连同它们拥有的常量。
- **R2 路径定位不变**：`upstream_check_script` 从**自身文件位置**解析同级 skill 与兄弟 checkout；新模块与 runner 位于同一 `scripts/` 目录，因此解析结果逐条不变；显式注入的环境变量仍然优先、缺失时仍然失败关闭。
- **R3 调用语义不变**：`--check` 与重建的调用形状（`[sys.executable, <script>, <program_root>]`）、超时、失败返回（`False`/`(None, error)`）、`result` 字段判定与“重建一次后重读”的顺序都不变。
- **R4 旧名字仍可用**：runner 保留全部被移动名字与常量的模块级入口；其中三个需要注入的名字（`load_contact_evidence`、`professor_source_state`、`resolve_contact_evidence`）保留同签名薄包装（见“方案”）。
- **R5 命名与语义不变**：`professor_source_state` 的姓名归一化仍用 runner 的 `compact_name`（显式注入，不复制第二份实现）。

**非目标（本批不动）**：证据快照与决策阶梯（`contact_evidence_record`、`contact_evidence_record_degraded`、`contact_evidence_snapshot`——它被 3 个测试文件直接引用、`contact_evidence_freshness_reason`、`evaluate_contact_evidence`、`_evaluate_record_ladder`、`evidence_provenance`、`contact_evidence_decisions`）——它们依赖阶梯内部函数与 `sha256_obj`、`VERIFY_TTL_DAYS`，属下一批；Stage3 校验交接（已在边界二完成）、Stage2 划分（等 #92）、测试分组／CI 评估（另评估）。

## 依据与关键事实

审核依据为项目 `PROJECT_CONSENSUS.md` 与 `Plan Reviewer Rule.md`；测试设计另按 `Test Engineer Rule.md` 审核。

| 决定 | 关键事实 | 来源（目标修订） |
| --- | --- | --- |
| 8 个函数的位置与规模 | `load_contact_evidence` 8373-8392、`upstream_check_script` 8395-8427、`run_contact_evidence_check` 8430-8440、`run_contact_evidence_rebuild` 8443-8462、`run_upstream_check_argv` 8465-8480、`professor_source_state` 8483-8497、`source_state_needs_rebuild` 8500-8509、`resolve_contact_evidence` 8512-8529 | `scripts/contact_state.py` |
| 常量 | `CONTACT_EVIDENCE_FILE` 148、`CONTACT_EVIDENCE_KIND` 149、`CONTACT_EVIDENCE_SCHEMAS` 150、`UPSTREAM_REPO_ID` 158、`UPSTREAM_SKILL_ID` 159、`UPSTREAM_CHECK_RESOURCE` 160、`UPSTREAM_SCRIPT_ENV` 162、`UPSTREAM_CHECK_TIMEOUT_SECONDS` 163 | 同上 |
| 耦合只有两个 runner 辅助函数（含传递） | 直接：`load_contact_evidence` → `read_json_file`，`professor_source_state` → `compact_name`；传递：`resolve_contact_evidence` 调 `load_contact_evidence`（8517、8524）与 `professor_source_state`（8521），因此它也必须拿到这两个注入值。其余自由名字只有 `os`/`sys`/`subprocess`/`json`/`Path` 与组内互引（签名不需要 `Any`） | AST 自由变量分析 |
| 路径解析依赖自身文件位置 | `upstream_check_script` 用 `Path(__file__).resolve().parents` 解析同级 `professor-collector` 与兄弟 checkout；新模块与 runner 同目录 → 解析结果不变 | `scripts/contact_state.py:8395-8427` |
| 测试直接引用（决定包装范围） | `upstream_check_script()`：`test_stage5_fixture_isolation.py:28`、`test_contact_state.py:3199`、`test_stage5_dualtarget_contract.py:358` 与 `:377`（均无参）；`load_contact_evidence(program_root)`：`test_stage5_fixture_isolation.py:32`（单参）；`run_upstream_check_argv(argv)`：`test_contact_state.py:3198`（单参）；`run_contact_evidence_check(program_root)`：`test_stage5_dualtarget_contract.py:359` 与 `:378`（单参）；`professor_source_state(report, 教授名)`：`test_stage5_dualtarget_contract.py:362`（两个位置参数） | 全仓测试检索 |
| 环境变量契约 | `UPSTREAM_SCRIPT_ENV` 显式注入优先、文件不存在时返回 `None`（失败关闭），未注入时按安装布局解析 | `scripts/contact_state.py:8411-8427` |
| 组外调用点共 5 处 | `cmd_stage4_finalize` 8221 与 `cmd_stage4_migrate_local` 8305 调 `load_contact_evidence(program_root)`；`contact_evidence_decisions` 8794 调 `professor_source_state(report, professor)`；`cmd_stage5_plan` 9407 与 `cmd_stage5_finalize` 10045 调 `resolve_contact_evidence(program_root, professors)`。五处**全部不改调用点**，靠同签名薄包装保持原签名。其余 5 个函数与 8 个常量在组外没有调用者 | AST 调用点统计 + 全仓检索 |
| 相邻模块加载做法 | runner 已按路径加载 `_stage3_render.py`、`_contact_io.py`、`_stage3_handoff.py`；`scripts/` 不保证在 `sys.path` | `scripts/contact_state.py` 顶部加载块 |
| 夹具已通用化 | 两个假安装布局夹具复制全部 `_*.py` 兄弟模块，本批无需改夹具 | `tests/test_stage5_immutable.py`、`tests/test_stage5_dualtarget_contract.py` |

## 方案

### 因果链

需求（上游联系证据的定位/检查/重建仍散在巨型 runner 中）→ 现行机制（8 个函数在 8373-8529 成块，耦合只有 8 个常量与 `read_json_file`／`compact_name` 两个辅助函数；`upstream_check_script` 依赖自身文件位置解析同级 skill）→ 变更点（函数与常量按行区间原样搬入同目录的 `_contact_evidence.py`；两个辅助函数以显式关键字参数注入；runner 保留别名与三个同签名包装）→ 行为变化（解析路径、调用形状、超时与返回值全部不变；`contact_state.<name>` 仍可用）→ 满足需求。

### 选定设计

**新模块 `scripts/_contact_evidence.py`**（与 runner 同目录，这是 R2 的前提）：

- 原样搬入 8 个函数与 8 个常量；常量在 runner 侧保留别名。
- 三处显式注入：`load_contact_evidence(program_root, *, read_json_file)`、`professor_source_state(report, professor, *, compact_name)`、`resolve_contact_evidence(program_root, professors, *, read_json_file, compact_name)`；模块内部互调时把注入值继续传下去（`resolve_contact_evidence` 调 `load_contact_evidence(..., read_json_file=read_json_file)` 与 `professor_source_state(..., compact_name=compact_name)`）。
- `upstream_check_script`、`run_contact_evidence_check`、`run_contact_evidence_rebuild`、`run_upstream_check_argv`、`source_state_needs_rebuild` 不需要 runner 侧注入（只用标准库、常量与组内函数）。
- 模块不 import runner、不复制 `read_json_file`/`compact_name`、不改 `sys.path`。

**runner 侧入口**：

- 8 个常量与 5 个函数（`upstream_check_script`、`run_contact_evidence_check`、`run_contact_evidence_rebuild`、`run_upstream_check_argv`、`source_state_needs_rebuild`）用同一对象别名；
- **三个同签名薄包装**（5 处保留调用点与测试直调都按原签名，因此一个调用点都不改）：`load_contact_evidence(program_root)` 注入 `read_json_file`；`professor_source_state(report, professor)` 注入 `compact_name`（测试以两个位置参数直调它）；`resolve_contact_evidence(program_root, professors)` 同时注入两个值；
- 三个包装之外，5 处组外调用点（8221／8305／8794／9407／10045）一律保持原样。

### 冻结的契约

- `upstream_check_script` 的三级解析顺序、显式注入优先与失败关闭不变；新模块必须与 runner 同目录（换目录会静默改变解析结果，属禁止项）。
- `run_upstream_check_argv` 的 `sys.executable`、超时、JSON 解析与 `(dict|None, error|None)` 返回形状不变。
- `run_contact_evidence_rebuild` 的调用形状（不带 `--check`）、`result == "ok"` 判定与 `bool` 返回不变。
- `resolve_contact_evidence` 的“先加载 + `--check`，必要时重建一次后重读”的顺序与返回字典的键不变；`unavailable` 不触发重建。
- `load_contact_evidence` 的 schema/kind 校验与 `(artifact, error)` 返回不变；`professor_source_state` 的姓名归一化仍用 runner 的 `compact_name`。
- runner 侧 `contact_state.<name>`（8 个函数 + 8 个常量）仍可用：5 个函数与 8 个常量是同一对象别名，`load_contact_evidence`／`professor_source_state`／`resolve_contact_evidence` 是同签名薄包装（本批的例外清单，原因分别是 4 处保留调用点与 1 处测试两参直调）。
- 夹具无需改动（已复制全部 `_*.py` 兄弟模块）。

### 替代方向与取舍

| 方向 | 不采用的原因 |
| --- | --- |
| 让新模块 import runner 取 `read_json_file`/`compact_name` | 循环导入；runner 可能被按路径加载，模块名不一定在 `sys.modules` |
| 在模块里复制这两个辅助函数的实现 | 出现第二份实现，`compact_name` 的归一化规则或 `read_json_file` 的错误分类一旦分叉不会被现有测试发现 |
| 把 `read_json_file`/`compact_name` 一起搬进本模块 | 它们是通用辅助（`read_json_file` 在 runner 内约 20 处使用），放进证据模块属职责错位 |
| 把新模块放在别的目录 | 会改变 `upstream_check_script` 的 `__file__` 解析结果，属路径定位破坏 |
| 连快照/决策阶梯一起搬 | 依赖阶梯内部函数与 `sha256_obj`、`VERIFY_TTL_DAYS`，会把批次扩成整个证据子系统 |

## 影响

- **intended_change**：上游证据定位/检查/重建的 8 个函数与 8 个常量移入同目录的 `_contact_evidence.py`；`read_json_file`/`compact_name` 改为显式注入；runner 保留别名与 `load_contact_evidence`／`professor_source_state`／`resolve_contact_evidence` 三个同签名包装。
- **preserved_behavior**：`upstream_check_script` 的三级解析与失败关闭；`--check`/重建调用形状、超时与返回值；`resolve_contact_evidence` 的顺序与返回键；`load_contact_evidence` 的校验；`professor_source_state` 的归一化；Stage5 plan/finalize 触发重建的既有行为；`contact_state.<name>` 可用性；CLI 与安装布局。
- **approved_behavior_change**：无。签名变化只发生在 runner 内部私有函数上；对测试暴露的 `upstream_check_script`／`load_contact_evidence`／`run_upstream_check_argv`／`run_contact_evidence_check`／`professor_source_state` 全部保持原签名，5 处保留调用点一个都不改。
- **prohibited_side_effect**：改变解析顺序或失败关闭；改变调用形状、超时或返回值；复制第二份 `compact_name`/`read_json_file`；把新模块放到别的目录；顺带搬快照/决策阶梯或其它边界；改测试断言。
- **unresolved impact**：无影响方案成立的项目。按三个同签名包装的方案，**runner 侧 8 个名字的签名全部保持原样**；新增的关键字参数只出现在 `_contact_evidence.py` 的内部函数上，仓库外反射 runner 名字不会看到签名变化。

## 关键安全条件与反例

必须一直成立的条件：

1. `upstream_check_script` 在相同环境下返回与今天相同的路径（或同样返回 `None`），包括显式注入、安装布局与兄弟 checkout 三种情况。
2. `resolve_contact_evidence` 的“不新鲜 → 重建一次 → 重读”顺序与返回键不变；`unavailable` 不重建。
3. `load_contact_evidence` 仍以单参数可用，schema/kind 校验与错误字符串不变。
4. `professor_source_state` 的归一化仍走 runner 的 `compact_name`（注入的是同一函数对象）。
5. runner 侧 5 个函数与 8 个常量的别名指向模块内同一对象；`load_contact_evidence`、`professor_source_state`、`resolve_contact_evidence` 三个同签名包装的入参与返回值与原函数一致。
6. 假安装布局夹具复制全部兄弟模块，复制出的 runner 能加载新模块。

代表性反例：

- 把新模块放到 `scripts/` 之外：`upstream_check_script` 的 `parents[1].parent` 会指向别处，checker 解析静默失败——禁止，测试里以“安装布局下能找到 sibling checker”的既有用例兜底。
- 模块里复制一份 `compact_name`：姓名归一化分叉，`professor_source_state` 的匹配会与 runner 其它地方不一致。
- 让模块版的 `resolve_contact_evidence` 直接以别名暴露：它会缺 `read_json_file`／`compact_name` 而在内部调用处 `TypeError`；因此必须走同签名包装。
- 把 `unavailable` 也当作需要重建：会向上游发起多余的重建调用，改变既有失败路径。
- 直接给 `load_contact_evidence`／`professor_source_state` 加必填参数：`test_stage5_fixture_isolation.py:32` 与 `test_stage5_dualtarget_contract.py:362` 的既有直调会 `TypeError`（后者是两个位置参数）。

## 实施位置与顺序

1. **计划审核**：本文件取得 `Plan conclusion: APPROVED`。
2. **本地执行代理**（按获批计划实施）：
   - 新增 `scripts/_contact_evidence.py`：8 个函数与 8 个常量按行区间原样搬入；三个函数加关键字注入（`load_contact_evidence`、`professor_source_state`、`resolve_contact_evidence`）；模块头部导入 `os`／`sys`／`subprocess`／`json`／`Path`。
   - `scripts/contact_state.py`：删除被搬走的定义与常量；加按路径加载；5 个函数与 8 个常量用同一对象别名；对 `load_contact_evidence`、`professor_source_state`、`resolve_contact_evidence` 三个名字加同签名薄包装（内部注入 `read_json_file`／`compact_name`）；**5 处组外调用点一个都不改**。
   - 夹具无需改动。
3. **测试准备与审核**：测试工程师按 `Test Engineer Rule.md` 准备测试资产（见同目录 `test-plan.md`）。共用自检清单随 PR #98 引入（`plan/test-plan-checklist.md`）；本批计划在合并前按同一口径自检，不把该文件已在本分支存在当作前提。
4. **正式执行**：测试计划获批后执行受影响测试并记录结果。

## 修订记录

- 第 1 版：首次提交计划审核。
- 第 3 版：按修订复核的三条非阻断措辞统一——因果链、intended_change、R4 与 unresolved impact 都改为“三个同签名包装”，并说明 runner 侧 8 个名字签名全部不变、新增关键字参数只在模块内部函数上。
- 第 2 版：按第 1 轮审核的五条 blocker 修正——B1 组外调用点补齐为 5 处（8221／8305／8794／9407／10045），逐处标注“靠包装、不改调用点”；B2 测试引用行按实际清单重写（`upstream_check_script` 3 个文件、`run_upstream_check_argv`、`run_contact_evidence_check`、`professor_source_state` 两位置参数直调），并把下一批的 `contact_evidence_snapshot` 移入非目标；B3／B4 方案改为**三个同签名薄包装**（`load_contact_evidence`／`professor_source_state`／`resolve_contact_evidence`），其余 5 个函数与 8 个常量用别名，解决 `resolve_contact_evidence` 的传递性注入与测试可见签名；B5 实施步骤与引用同步（合并顺序补 #97、checklist 引用改为“随 #98 引入”）。非阻断项一并处理：去掉 `Any`、精简模块头部导入。

## 审核状态

计划第 3 版为当前唯一计划，结论 **`Plan conclusion: APPROVED`**（P1–P4 全 PASS；独立计划审核于 2026-10-19 给出）。第 1 版结论 `NEEDS_MODIFICATION`（B1–B5）、第 2 版按 B1 修正后获批，均已按上节记录。后续审核以本文件、需求原文、`PROJECT_CONSENSUS.md` 与 `Plan Reviewer Rule.md` 为输入。
