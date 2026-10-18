# 边界四：把联系证据的快照与决策阶梯移入内部模块（执行计划）

## 版本、来源与状态

- 需求来源：负责人 2026-10-18“其余边界”原文中的“Stage4/5 证据处理”；本批是它的后半（快照与决策阶梯），前半（上游定位、检查与重建）已由边界三（PR #101）完成。
- Requirement revision: 第 1 版（边界四：证据快照与决策阶梯）。
- Canonical Plan revision: 第 2 版。
- Target repository revision: `cdd01f7f2c03be822adbb5a4117c7e65a89d6c82`（分支 `refactor-contact-evidence`，已含批次二/三与边界一/二/三）。
- Implementation sequencing prerequisite: PR #98、#99、#100、#101 均未合并；本批堆叠在 #101 之上，合并顺序 #98 → #99 → #100 → #101 → 本批。
- Relevant upstream/runtime revision: 上游 `professor-research` 的 `contact_evidence.py` 不在本仓；本批只动调用侧，不改它的接口。
- Proposed review status: pending。
- 唯一规范来源：本文件。

## 正式需求与范围

- **R1 抽快照与决策层**：把证据快照与决策阶梯移入内部模块：`contact_evidence_record`、`contact_evidence_record_degraded`、`contact_evidence_snapshot`、`evidence_provenance`、`contact_evidence_freshness_reason`、`evaluate_contact_evidence`、`_evaluate_record_ladder`、`contact_evidence_decisions` 共 8 个函数，连同它们拥有的 2 个常量。
- **R2 判定语义不变**：阶梯的 `status`／`reason_code`／`web_lookup_required`／`recipient_email` 等返回字段与优先级顺序逐项不变；降级记录、冲突升级、`official_only` 可用性等既有分支不因搬移改变。
- **R3 时间与新鲜度不变**：`contact_evidence_freshness_reason` 仍按 runner 的 `VERIFY_TTL_DAYS`（30 天）判定，注入的是同一个值，不复制常量。
- **R4 旧名字仍可用**：runner 保留全部被移动名字与常量的模块级入口；`contact_evidence_snapshot` 因有组外调用点与 3 个测试文件直调，保留同签名薄包装。
- **R5 同一模块、同一目录**：8 个函数加入边界三建立的 `scripts/_contact_evidence.py`（同目录），不新建第二个证据模块；`upstream_check_script` 的 `__file__` 解析链不受影响（该文件位置不变）。

**非目标（本批不动）**：上游定位/检查/重建（已在边界三完成）；`VERIFY_TTL_DAYS` 常量本身（它同时服务校验缓存，属别处职责，本批只注入）；Stage4/5 的事务与选择路径；Stage3 校验交接；Stage2 划分（等 #92）；测试分组／CI 评估。

## 依据与关键事实

审核依据为项目 `PROJECT_CONSENSUS.md` 与 `Plan Reviewer Rule.md`；测试设计另按 `Test Engineer Rule.md` 审核。

| 决定 | 关键事实 | 来源（目标修订） |
| --- | --- | --- |
| 8 个函数连续成块 | `contact_evidence_record` 8411-8421、`contact_evidence_record_degraded` 8424-8446、`contact_evidence_snapshot` 8449-8472、`evidence_provenance` 8475-8484、`contact_evidence_freshness_reason` 8487-8507、`evaluate_contact_evidence` 8510-8606、`_evaluate_record_ladder` 8609-8661、`contact_evidence_decisions` 8664-8675（即 8411-8675 连续区间） | `scripts/contact_state.py` |
| 要搬的常量 | `CONTACT_EVIDENCE_SCHEMA_LIVE` 197（块内仅 8584 使用）、`CONTACT_EVIDENCE_VERDICTS` 198-199（块内仅 8641 使用）→ 只被搬移块使用，随函数搬移 | 同上 |
| 不搬的常量 | `VERIFY_TTL_DAYS` 255：块外只有 8795 一处真实使用（校验缓存路径），块内两处文档串（8491、8543）与一处真实使用（8505）→ 保留在 runner、以参数注入 | 同上 |
| 注入点三个、沿调用链完整传递 | 直接使用者：`contact_evidence_record` → `compact_name`；`contact_evidence_snapshot` → `sha256_obj` 且在 8454 调 `contact_evidence_record` → 还需 `compact_name`；`contact_evidence_freshness_reason` → `verify_ttl_days`。传递：`_evaluate_record_ladder` 调 `contact_evidence_freshness_reason`（8609-8661 内第 11 行＝8619）、`contact_evidence_record`（第 14 行＝8622）与 `sha256_obj`（第 20 行＝8628）→ 需要三者；`evaluate_contact_evidence` 两次调 `_evaluate_record_ladder`（8510-8606 内第 77、96 行＝8586、8605）→ 需要三者；`contact_evidence_decisions` 调 `evaluate_contact_evidence` 与 `professor_source_state`（后者由边界三搬入，模块版需要 `compact_name`）→ 需要三者 | symtable 自由名 + 逐行核对 |
| 嵌套函数随宿主搬移 | `accept`／`escalate`／`needs_refresh` 是 `evaluate_contact_evidence` 内部的嵌套定义（8549／8555／8565），不是模块级名字 | `scripts/contact_state.py:8549-8575` |
| 组外调用点只有 3 处 | `contact_evidence_snapshot` 在 8074（Stage4 finalize 路径，三位置参数）；`contact_evidence_decisions` 在 9289 与 9927（stage5-plan 与 finalize，两位置参数）。其余 6 个函数在组外没有调用者 | AST 调用点统计 |
| 测试直调（决定包装范围） | `contact_state.contact_evidence_snapshot(frozen, None, name)`（`test_contact_state.py:1440`、`test_stage5_fixture_isolation.py:39`、`test_contact_evidence_ladder.py:441`，均三位置参数）；`contact_state.evaluate_contact_evidence("佐藤 花子", snapshot, artifact, None, checker_error="script_missing")`（`test_contact_evidence_ladder.py:443`，四位置参数 + 关键字）。两者都必须保持原签名 | 全仓测试检索 |
| 决策字段被测试断言 | 阶梯测试断言 `status`／`reason_code`／`web_lookup_required`／`recipient_email` 等字段（`test_contact_evidence_ladder.py` 共 30+ 项） | 同上 |
| 相邻模块加载做法 | runner 已按路径加载 `_stage3_render.py`、`_contact_io.py`、`_stage3_handoff.py`、`_contact_evidence.py`；`scripts/` 不保证在 `sys.path` | `scripts/contact_state.py` 顶部加载块 |
| 夹具已通用化 | 两个假安装布局夹具按 `glob("_*.py")` 复制全部兄弟模块，本批无需改夹具 | `tests/test_stage5_immutable.py`、`tests/test_stage5_dualtarget_contract.py` |

## 方案

### 因果链

需求（证据快照与决策阶梯仍散在巨型 runner 中）→ 现行机制（8 个函数在 8411-8675 连续成块；耦合只有 `compact_name`／`sha256_obj`／`VERIFY_TTL_DAYS` 与两个证据常量；组外只有 3 处调用点，另有 4 处测试直调）→ 变更点（函数与两个常量搬入边界三建立的同目录 `_contact_evidence.py`；三个依赖以显式关键字参数注入；runner 保留别名与 `contact_evidence_snapshot` 同签名包装）→ 行为变化（阶梯判定、字段、TTL 与 `contact_state.<name>` 可用性全部不变）→ 满足需求。

### 选定设计

**在既有 `scripts/_contact_evidence.py` 里追加**（不新建模块，保持证据职责集中；文件位置不变，因此 `upstream_check_script` 的 `__file__` 解析链不受影响）：

- 原样搬入 8 个函数与 `CONTACT_EVIDENCE_SCHEMA_LIVE`、`CONTACT_EVIDENCE_VERDICTS` 两个常量；常量在 runner 侧保留别名。
- 三个注入值沿调用链显式传递：`compact_name`、`sha256_obj`、`verify_ttl_days`。带这些参数的模块函数（六个）：`contact_evidence_record(artifact, professor, *, compact_name)`；`contact_evidence_snapshot(artifact, artifact_error, professor, *, compact_name, sha256_obj)`（8454 调 record 需要 `compact_name`）；`contact_evidence_freshness_reason(timestamp, *, verify_ttl_days)`；`_evaluate_record_ladder(..., *, compact_name, sha256_obj, verify_ttl_days)`；`evaluate_contact_evidence(..., *, compact_name, sha256_obj, verify_ttl_days)`（8586／8605 调 ladder）；`contact_evidence_decisions(emails, resolved, *, compact_name, sha256_obj, verify_ttl_days)`。模块内部互调时把注入值原样往下传。
- 模块 docstring 从“上游定位、检查与重建”扩展为“联系证据的上游定位、检查、重建、快照与决策阶梯”。

**runner 侧入口**：

- 2 个常量与 5 个函数用同一对象别名（`contact_evidence_record`、`contact_evidence_record_degraded`、`evidence_provenance`、`contact_evidence_freshness_reason`、`_evaluate_record_ladder`）；
- **三个同签名薄包装**（覆盖 3 处组外调用点与 4 处测试直调，因此一个调用点都不改）：`contact_evidence_snapshot(artifact, artifact_error, professor)` 注入 `compact_name` 与 `sha256_obj`；`evaluate_contact_evidence(...)` 注入三者（测试按四位置参数 + `checker_error=` 直调）；`contact_evidence_decisions(emails, resolved)` 注入三者（组外 9289／9927 直调）；
- 3 处组外调用点（8074、9289、9927）**一个都不改**。

### 冻结的契约

- 阶梯判定的字段与优先级：`status`、`reason_code`、`web_lookup_required`、`recipient_email`、`sources` 等与今天逐项相同；冲突升级、降级记录、`official_only` 可用性、`paper_only` 不提升等既有分支不变。
- `contact_evidence_snapshot` 的 sha 绑定与返回形状不变；`contact_evidence_record` 的姓名归一化仍用 runner 的 `compact_name`。
- `contact_evidence_freshness_reason` 仍以 30 天（`VERIFY_TTL_DAYS`）为界，注入的是同一个值。
- `contact_evidence_decisions` 的逐教授路由与返回键不变。
- runner 侧 `contact_state.<name>`（8 个函数 + 2 个常量）仍可用：5 个函数与 2 个常量是同一对象别名，`contact_evidence_snapshot`／`evaluate_contact_evidence`／`contact_evidence_decisions` 是同签名薄包装（本批的例外清单）。
- 模块仍与 runner 同目录；`_contact_evidence.py` 不 import runner、不复制第二份实现、不改 `sys.path`。
- 夹具无需改动。

### 替代方向与取舍

| 方向 | 不采用的原因 |
| --- | --- |
| 新建 `_contact_evidence_ladder.py` | 与边界三的模块职责重叠；两个模块都要注入同一批辅助函数，反而增加耦合面 |
| 把 `VERIFY_TTL_DAYS` 一起搬进模块 | 块外仅 8795 一处真实使用（校验缓存路径），块内两处文档串与一处真实使用（8505）；搬走会造成职责错位 |
| 复制 `sha256_obj`／`compact_name` 实现 | 出现第二份实现，序列化或归一化规则分叉不会被现有测试发现 |
| 给 `contact_evidence_snapshot` 直接加必填关键字参数 | 8074 与 3 个测试文件的既有直调会 `TypeError`（测试明确禁止改断言） |
| 连上游定位/检查/重建一起重排 | 已在边界三落地并获批，本批不重开 |

## 影响

- **intended_change**：证据快照与决策阶梯的 8 个函数与 2 个常量移入既有 `_contact_evidence.py`；`compact_name`／`sha256_obj`／`verify_ttl_days` 改为显式注入；runner 保留别名与 `contact_evidence_snapshot` 的同签名包装。
- **preserved_behavior**：阶梯判定的全部字段与优先级；降级/冲突/不可用分支；sha 绑定；TTL 判定；逐教授路由；`contact_state.<name>` 可用性；Stage4/5 与 Stage3 的既有流程；CLI 与安装布局。
- **approved_behavior_change**：无。签名变化只发生在 runner 内部函数上；对测试暴露的 `contact_evidence_snapshot` 与 `evaluate_contact_evidence`、对组外暴露的 `contact_evidence_decisions` 全部保持原签名，3 处组外调用点与 4 处测试直调一个都不改。
- **prohibited_side_effect**：改变阶梯判定或字段；复制第二份 `sha256_obj`/`compact_name`/TTL 常量；把新代码放到别的目录；改测试断言；顺带搬上游层或其它边界。
- **unresolved impact**：三个包装（`contact_evidence_snapshot`／`evaluate_contact_evidence`／`contact_evidence_decisions`）在 runner 侧保持原签名；另三个别名（`contact_evidence_record`／`contact_evidence_freshness_reason`／`_evaluate_record_ladder`）会暴露新增关键字参数，但仓内没有调用者、测试也没有直调，不影响兼容。

## 关键安全条件与反例

必须一直成立的条件：

1. 阶梯判定的字段与优先级逐项不变（含冲突升级与 `paper_only` 不提升）。
2. `contact_evidence_snapshot` 仍以三位置参数可用，sha 绑定不变。
3. `contact_evidence_freshness_reason` 的 30 天边界不变（注入的是同一个值）。
4. `contact_evidence_decisions` 的逐教授路由与返回键不变。
5. runner 侧 5 个函数与 2 个常量的别名指向模块内同一对象（其中 3 个别名带新增关键字参数，仓内无调用者）；`contact_evidence_snapshot`、`evaluate_contact_evidence`、`contact_evidence_decisions` 三个同签名包装的入参与返回值与原函数一致。
6. `_contact_evidence.py` 与 runner 同目录，夹具复制全部 `_*.py` 后仍能加载。

代表性反例：

- 忘记把 `verify_ttl_days`／`sha256_obj`／`compact_name` 沿 `_evaluate_record_ladder` → `evaluate_contact_evidence` → `contact_evidence_decisions` 传下去：链上任一调用处 `TypeError`，阶梯用例立刻失败（这正是边界三 B3 的同型错误）。
- 只给 `contact_evidence_snapshot` 包一层而让 `evaluate_contact_evidence` 以别名暴露：测试的四位置参数直调会缺 `sha256_obj`／`verify_ttl_days` 而 `TypeError`。
- 在模块里复制一份 `sha256_obj`：快照摘要与 runner 其它地方分叉，sha 绑定类断言会失败。
- 把 `contact_evidence_snapshot` 直接以别名暴露：8074 与 3 个测试文件的直调 `TypeError`。
- 把 8 个函数放进新目录的模块：边界三的 `upstream_check_script` 解析链前提被破坏（该函数虽不在本批搬移范围，但同文件位置必须保持）。
- 改动阶梯的优先级顺序：`test_contact_evidence_ladder.py` 的 30+ 项断言会失败，但若只改顺序而不改字段，可能只有部分失败——因此 T2 的对照必须逐字段比较完整决策对象。

## 实施位置与顺序

1. **计划审核**：本文件取得 `Plan conclusion: APPROVED`。
2. **本地执行代理**：
   - `scripts/_contact_evidence.py`：追加 8 个函数与 2 个常量；六个函数加关键字注入（`contact_evidence_record`、`contact_evidence_snapshot`、`contact_evidence_freshness_reason`、`_evaluate_record_ladder`、`evaluate_contact_evidence`、`contact_evidence_decisions`）；补运行期导入 `from datetime import datetime, timedelta, timezone`（`Any` 仅注解，已由 `from __future__ import annotations` 覆盖）；更新模块 docstring（注入面从 `read_json_file`／`compact_name` 扩为 `read_json_file`／`compact_name`／`sha256_obj`／`verify_ttl_days`）。
   - `scripts/contact_state.py`：删除被搬走的定义与 2 个常量；5 个函数与 2 个常量加别名；对 `contact_evidence_snapshot`（注入 `compact_name`＋`sha256_obj`）、`evaluate_contact_evidence`（注入三者）、`contact_evidence_decisions`（注入三者）加同签名薄包装；**3 处组外调用点不改**。
   - 夹具无需改动。
3. **测试准备与审核**：测试工程师按 `Test Engineer Rule.md` 准备测试资产（见同目录 `test-plan.md`，按共用清单 `plan/test-plan-checklist.md` 自检；该清单随 PR #98 引入，本分支暂不存在）。
4. **正式执行**：测试计划获批后执行受影响测试并记录结果。

## 修订记录

- 第 1 版：首次提交计划审核。
- 第 2 版：按第 1 轮审核的 B1 修正注入闭包——`contact_evidence_snapshot` 补 `compact_name`（8454 调 record）、`evaluate_contact_evidence` 补 `compact_name`（8586／8605 经 ladder 调 record），三个包装的注入集与模块内互调同步；另按非阻断项更正两个常量的行号（197／198-199）、`VERIFY_TTL_DAYS` 的块外使用数（仅 8795 一处）、“组外无调用者的函数”数（6 个）、runner 侧签名表述（三个包装保持原签名、三个别名暴露新参数但仓内无调用者），并在实施步骤补 `datetime`／`timedelta`／`timezone` 导入与 docstring 更新。

## 审核状态

计划第 2 版为当前唯一计划。第 1 版结论 `NEEDS_MODIFICATION`（B1），已按上节修正。后续审核以本文件、需求原文、`PROJECT_CONSENSUS.md` 与 `Plan Reviewer Rule.md` 为输入。
