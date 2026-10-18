# 边界二：把 Stage 3 校验交接的解析与写入原语移入内部模块（执行计划）

## 版本、来源与状态

- 需求来源：负责人 2026-10-18 三批要求中的“其余边界”原文：

  > 共享错误通道、事务／回滚、Stage3 提交与校验交接、Stage4/5 证据处理：先按常规审核。移动时可能改变共享状态、异常类型或路径定位，不能仅保留旧函数名就认定等价。

- Requirement revision: 第 1 版（边界二：Stage3 校验交接）。
- Canonical Plan revision: 第 3 版。
- Target repository revision: `779fb692ed5ded163ab0eb5b415aef698135f54e`（分支 `refactor/shared-error-and-commit`，已含批次二、批次三与边界一）。
- Implementation sequencing prerequisite: PR #97、#98、#99 尚未合并；本批堆叠在 #99 之上，合并顺序 #97 → #98 → #99 → 本批。上游 PR 改写时按受影响范围重放。
- Relevant upstream/runtime revision: N/A；不涉及外部仓库、CLI、安装布局或代理入口。
- Proposed review status: pending。
- 唯一规范来源：本文件。本文件只定义实施方案，不声明计划审核、测试审核或合并关口已经通过。

## 正式需求与范围

- **R1 抽原语**：把 Stage 3 校验交接的**解析与写入原语**移入一个内部模块：缓冲式持久写入（含文件身份与失败清理）、严格 JSON 对象解析、invocation 参数映射、校验结果归一化、渲染作用域标记解析、轮次守卫。
- **R2 语义不变**：退出码、错误 JSON 字段、异常类型与抛出时机、写入字节、文件身份判定、清理行为、路径解析与作用域解析结果都与今天相同；`fail` 的业务通道语义不变（通道开启时抛 `ProfessorBusinessFailure`，否则打印并退出 1）。
- **R3 模块边界明确**：新模块不 import runner；它需要的共享失败通道由**调用点显式传入**（关键字参数 `fail`），而不是复制一份或读取全局。
- **R4 旧名字仍可用**：runner 保留全部被移动名字的模块级入口——13 个名字与 3 个常量是同一对象别名，`stage3_render_line_scopes` 是同签名薄包装（唯一例外）——因此既有调用点与测试的 `contact_state.<name>` 引用不变。

**非目标（本批明确不动，并说明原因）**：

- 四个 CLI 处理器 `cmd_stage3_prepare_validation` / `cmd_stage3_write_validation` / `cmd_stage3_save_validation` / `cmd_stage3_record_validation`：它们依赖 `load_candidate_state` / `load_input_pack` / `_stage3_bound_render` / `_stage3_candidates_entry` / `stage3_validation_evidence` 等 runner 侧状态与渲染绑定函数，移动需要宽面注入并把 Stage3 的状态读取一并搬迁，超出“移动原语”的范围。
- 凭证与交接文件层（`_write_stage3_invocation` / `_read_stage3_invocation` / `_require_invocation_source` / `_stage3_handoff_directory` / `_load_stage3_handoff`）：依赖路径守卫 `require_professor_dir_under_program`、`profile_fingerprint` 与若干常量，属“凭证与交接文件”另一次拆分。
- Stage3 的提交路径（`managed_write` / `staged_pair_commit` 的调用点）与受管文件语义：`staged_pair_commit` 已在边界一移入 `_contact_io`，受管文档写入属另一组。
- Stage4/5 证据处理：另立 PR。

## 依据与关键事实

审核依据为项目 `PROJECT_CONSENSUS.md` 与 `Plan Reviewer Rule.md`；测试设计另按 `Test Engineer Rule.md` 审核。

| 决定 | 关键事实 | 来源（目标修订） |
| --- | --- | --- |
| 本批 14 个函数的位置与规模 | `_stage3_marker_payload` 5566-5571、`stage3_render_line_scopes` 5574-5618、`scope_key` 5621-5629、`_stage3_issue_scopes` 5650-5665、`_stage3_validation_files` 5668-5673、`_stage3_normalized_absolute_path` 5715-5724、`_stage3_complete_write_result` 5727-5799、`_stage3_args_from_invocation` 6171-6201、`_require_stage3_handoff_round` 6206-6244、`_stage3_json_object_pairs` 6413-6419、`_stage3_json_reject_constant` 6422-6423、`_stage3_created_file_identity` 6426-6428、`_stage3_cleanup_incomplete_write` 6431-6439、`_stage3_write_buffer` 6442-6475 | `scripts/contact_state.py` |
| 纯标准库、无需注入的部分 | `_stage3_created_file_identity`、`_stage3_cleanup_incomplete_write`、`_stage3_write_buffer`、`_stage3_json_object_pairs`、`_stage3_json_reject_constant`、`_stage3_args_from_invocation` 的自由名字只有 `os`/`Path`/`types`/`vars`/`Any`/`ValueError` 与组内互引 | AST 自由变量分析（脚本见测试记录） |
| 需要失败通道的部分 | `_stage3_normalized_absolute_path`、`_stage3_validation_files`、`_stage3_complete_write_result`、`_stage3_issue_scopes`、`_stage3_marker_payload`、`_require_stage3_handoff_round` 直接调用 `fail`（`_stage3_marker_payload` 另用 `json`）；`stage3_render_line_scopes` 只经 `_stage3_marker_payload` 间接使用。`scope_key` 是纯函数，不需注入 | 同上 |
| 需要随函数移动的常量 | `CANDIDATE_META_PREFIX` 5546、`STAGE3_SCOPE_PREFIX` 5547、`STAGE3_VALIDATION_MAX_ROUNDS` 5548（runner 另有 11739／11741／11747 使用它，因此别名必要） | 同上 |
| 调用面 | runner 内对这 14 个名字的调用共 24 处：16 处在保留代码、8 处在被移动函数内部。**测试另有两处直接引用**：`contact_state.stage3_render_line_scopes`（`tests/test_contact_state.py` 1724／1780／1800／1921，均为单参数调用）与 `contact_state.scope_key`（1725／1782／1803／1922） | AST 调用点统计 + 全仓检索 |
| 失败语义 | `fail` 在通道关闭时打印 `{"status": "error", "reason_code", "message", **extra}` 并以 1 退出；通道开启时抛 `ProfessorBusinessFailure` 且不打印不退出（边界一已移入 `_contact_io`） | `_contact_io.py`、边界一测试记录 |
| 校验定位依赖渲染文本 | `stage3_render_line_scopes` 按 `CANDIDATE_META_PREFIX` / `STAGE3_SCOPE_PREFIX` 与“标题后四行内”邻接解析渲染出的 Markdown（5596-5616）；消费者是保留代码 `stage3_validation_evidence`（调用 5827，issue 归域 5835） | `scripts/contact_state.py:5574-5618`、`5802-5840` |
| 相邻模块加载做法 | runner 已用 `Path(__file__).with_name(...)` + `spec_from_file_location` 加载 `_stage3_render.py` 与 `_contact_io.py`；`scripts/` 不保证在 `sys.path` | `scripts/contact_state.py:30-60` |
| 复制 runner 的夹具已通用化 | 两个假安装布局夹具复制**所有** `_*.py` 兄弟模块，因此新增模块无需再改夹具（边界一已做） | `tests/test_stage5_immutable.py:218-222`、`tests/test_stage5_dualtarget_contract.py:330-333` |

## 方案

### 因果链

需求（Stage3 校验交接的解析/写入原语继续留在巨型 runner 顶部与中段、相互分散）→ 现行机制（14 个函数散落在 5546-6475 之间，`fail` 与 3 个常量是它们与 runner 的唯一耦合；调用点全在 runner 内）→ 变更点（把 14 个函数与 3 个常量按行区间原样搬入 `_stage3_handoff.py`；需要失败通道的 7 个函数改为接收显式关键字参数 `fail`，runner 在保留的 9 处调用点与唯一一个同签名包装里把现有 `fail` 传进去；runner 保留 13 个名字与 3 个常量的别名）→ 行为变化（用户可见行为不变；runner 的这些名字改由模块提供，调用点只多一个显式参数）→ 满足需求。

### 选定设计

**新模块 `scripts/_stage3_handoff.py`**（下划线前缀沿用内部辅助模块约定）：

- 原样搬入：`_stage3_marker_payload`、`stage3_render_line_scopes`、`scope_key`、`_stage3_issue_scopes`、`_stage3_validation_files`、`_stage3_normalized_absolute_path`、`_stage3_complete_write_result`、`_stage3_args_from_invocation`、`_require_stage3_handoff_round`、`_stage3_json_object_pairs`、`_stage3_json_reject_constant`、`_stage3_created_file_identity`、`_stage3_cleanup_incomplete_write`、`_stage3_write_buffer`；
- 随函数搬入的常量：`CANDIDATE_META_PREFIX`、`STAGE3_SCOPE_PREFIX`、`STAGE3_VALIDATION_MAX_ROUNDS`（runner 侧保留别名）；
- **接口改动**：七个会触发失败的函数改成关键字参数 `fail`（`_stage3_marker_payload(..., *, fail)`、`stage3_render_line_scopes(..., *, fail)`、`_stage3_normalized_absolute_path(..., *, fail)`、`_stage3_validation_files(..., *, fail)`、`_stage3_complete_write_result(..., *, fail)`、`_stage3_issue_scopes(..., *, fail)`、`_require_stage3_handoff_round(..., *, fail)`）；模块内部互调时把 `fail` 继续传下去（`_stage3_complete_write_result` 内两处、`stage3_render_line_scopes` 内两处）。
- **唯一的签名例外**：`stage3_render_line_scopes` 被测试以单参数直调（4 处），因此 runner 侧对这一个名字保留**同签名薄包装** `def stage3_render_line_scopes(md_text): return _stage3_handoff.stage3_render_line_scopes(md_text, fail=fail)`；其余 13 个名字都是同一对象别名。包装的存在与理由写进冻结契约。
- 模块不 import runner、不定义第二份失败通道、不复制 `_contact_io`。

**runner 侧加载与入口**：沿用既有按路径加载做法。13 个名字与 3 个常量以别名回到 runner 命名空间；`stage3_render_line_scopes` 用同签名薄包装（见上）。**只在保留代码调用那六个需 `fail` 的函数的 9 处**补 `fail=fail`（5684、6492、6516、6532、10949、5835、6352、6596、11718），`fail` 是 runner 命名空间里的 `_contact_io.fail` 别名，因此业务通道语义不变；纯函数调用与 `6486/6487`、`6504/6505` 的 json hook 参数引用不加该关键字。

### 冻结的契约

- 六个函数的失败行为：`fail` 的调用参数（`reason_code`、`message`、`**extra`）逐字不变，因此错误 JSON 与退出码不变；通道开启时仍抛 `ProfessorBusinessFailure`。
- `_stage3_write_buffer` 的写入语义：`os.open(path, O_RDWR|O_CREAT|O_EXCL, 0o600)` + `os.fchmod(fd, 0o600)`、逐次 `os.write` 直到写完、`os.fsync`、随后 `os.lseek` 回读并按 64 KiB 分块与写入缓冲比对（不一致抛 `OSError`）、失败时按创建时的 `st_dev`/`st_ino` 身份清理（身份不一致则不删）——全部不变。
- 严格 JSON 解析：`object_pairs_hook`、拒绝 `NaN`/`Infinity`（`parse_constant`）的行为不变；非法输入抛 `ValueError`。
- `_stage3_args_from_invocation` 的 `types.SimpleNamespace`/`vars` 映射与“只覆盖 invocation 记录的来源参数”不变。
- `stage3_render_line_scopes` 的解析结果不变（标记前缀、邻接规则、返回的 scope 列表顺序与内容）。
- `_require_stage3_handoff_round` 的轮次上限来自 `STAGE3_VALIDATION_MAX_ROUNDS`，失败原因码不变。
- runner 侧 `contact_state.<name>`（含三个常量）仍可用：13 个名字与 3 个常量是同一对象别名，`stage3_render_line_scopes` 是唯一同签名薄包装（因测试单参数直调）。

### 替代方向与取舍

| 方向 | 不采用的原因 |
| --- | --- |
| 让新模块 import `_contact_io` 取 `fail` | 会加载出第二个 `_contact_io` 实例，业务通道状态分裂（边界一刚冻结“一个模块实例一份状态”） |
| 加载后给模块属性赋 `fail` | 隐式全局状态，函数签名上看不到依赖 |
| 把 `fail` 作为模块级默认值/全局变量再补丁 | 同上，且测试无法独立验证 |
| 连凭证/交接文件层与四个 CLI 处理器一起搬 | 需要宽面注入（状态与 pack 载入、渲染绑定、路径守卫）并把 Stage3 状态读取一并搬迁，风险远超“移动原语” |
| 只搬纯标准库的 6 个函数 | 会让“其余八个函数”继续散落，且 `fail` 注入机制迟早要建；本批一次建好 |

## 影响

- **intended_change**：14 个 Stage3 校验交接原语与 3 个常量移入 `_stage3_handoff.py`；七个函数改为显式接收 `fail`；runner 保留 13 个别名与一个同签名包装，并在保留下来的 9 处调用点传 `fail=fail`。
- **preserved_behavior**：错误 JSON 与退出码、业务通道异常语义、缓冲写入的字节/权限/身份/清理、严格 JSON 解析、invocation 参数映射、校验结果归一化、渲染作用域解析结果、轮次守卫、`contact_state.<name>` 可用性、CLI 与安装布局。
- **approved_behavior_change**：无。被移动函数都是 runner 内部原语，没有对外 CLI 或文件格式变化；唯一签名变化发生在 runner 内部私有函数上，且调用点同批更新。
- **prohibited_side_effect**：改变错误码或退出码；改变写入缓冲的权限/分块/清理；改变作用域解析结果；把失败通道复制成第二份；顺带搬 CLI 处理器、凭证层或受管文档写入；改测试断言。
- **unresolved impact**：无影响方案成立的项目。仓库外若有人按名字反射 `contact_state.<私有函数>` 并依赖其签名，会看到多出的关键字参数；这些是下划线私有函数，仓库内没有这种调用者。

## 关键安全条件与反例

必须一直成立的条件：

1. 六个函数在同样的非法输入下给出**同样的错误 JSON 与退出码**，业务通道开启时抛同一个 `ProfessorBusinessFailure`。
2. `_stage3_write_buffer` 写出的文件字节与今天相同；中途失败时按文件身份删除本次写入的文件，且不删除别人的文件。
3. 严格 JSON 解析对 `NaN`/`Infinity`/重复键/非对象输入的行为不变。
4. `stage3_render_line_scopes` 对同一份渲染文本返回逐项相同的作用域列表（用于校验定位）。
5. `_require_stage3_handoff_round` 的轮次判定与失败原因码不变。
6. runner 保留下来的 9 处调用点与新签名一致；13 个名字与 3 个常量别名后与模块内是同一个对象，`stage3_render_line_scopes` 的包装保持原签名与返回值。

代表性反例：

- 模块自己 import `_contact_io`：业务通道状态分裂，Stage4 逐教授失败行会退回“进程退出”——禁止。
- 忘记给某个调用点补 `fail`：调用时 `TypeError`，现有用例会立刻失败。
- 把 `_stage3_write_buffer` 的 `0o600`／`fsync`／回读比对换成 `Path.write_bytes`：写入字节看似相同，但文件权限与“写完即可读到相同字节”的保证都变了（该函数不使用 `os.replace`，与 issue67 注入无关）。
- 把 `stage3_render_line_scopes` 的“标题后四行内”邻接规则改成无界搜索：校验定位会吸走别的标记，`test_stage3_validation_refine` 的 scope 断言会失败。
- 把三个常量留在 runner、模块内再用注入值：两份取值可能分叉；本方案让常量随函数走、runner 只做别名。

## 实施位置与顺序

1. **计划审核**：本文件取得 `Plan conclusion: APPROVED`。
2. **本地执行代理**（按获批计划实施）：
   - 新增 `scripts/_stage3_handoff.py`：14 个函数与 3 个常量按行区间原样搬入，七个函数（含 `stage3_render_line_scopes`）加关键字参数 `fail`。
   - `scripts/contact_state.py`：删除被搬走的定义与常量；加按路径加载、13 个名字与 3 个常量的别名，以及 `stage3_render_line_scopes` 的同签名薄包装；只给**保留代码里调用那六个需 `fail` 的函数**的 9 处补 `fail=fail`（`_stage3_validation_files` 5684；`_stage3_complete_write_result` 6492；`_stage3_normalized_absolute_path` 6516／6532／10949；`_stage3_issue_scopes` 5835；`_require_stage3_handoff_round` 6352／6596／11718）。纯函数调用（`scope_key`、`_stage3_write_buffer`、`_stage3_args_from_invocation`）与把 `_stage3_json_object_pairs`／`_stage3_json_reject_constant` 当参数传入的引用（6486／6487、6504／6505）**不得**加该关键字。
   - 新模块头部导入：`from __future__ import annotations`、`import json`、`import os`、`import types`、`from pathlib import Path`、`from typing import Any`。
   - 夹具无需改动（已复制所有 `_*.py` 兄弟模块）。
3. **测试准备与审核**：测试工程师按 `Test Engineer Rule.md` 准备测试资产（见同目录 `test-plan.md`）。
4. **正式执行**：测试计划获批后执行受影响测试并记录结果；未受影响的通过结果沿用。

## 修订记录

- 第 1 版：首次提交计划审核。
- 第 2 版：按第 1 轮审核的四条 blocker 修正——① 事实行改正“无外部引用”的错误：测试对 `stage3_render_line_scopes`（4 次单参调用）与 `scope_key`（4 次）有直接引用；② 契约改正 `_stage3_write_buffer` 的权限（`0o600`，含 `fchmod`）并补上“写后 `lseek` 回读、64 KiB 分块比对、不一致抛 `OSError`”，依赖枚举补 `json`/`scope_key`，消费者行号改为 5827／5835；③ `stage3_render_line_scopes` 改为 runner 侧同签名薄包装（唯一签名例外），其余 13 个名字仍是同一对象别名；④ 实施步骤改为精确三类调用点清单（保留代码 9 处补 `fail=`；模块内互调随搬移传参；纯函数与 json hook 引用不动）并写明新模块头部导入。
- 第 3 版：按修订复核的两条非阻断措辞修正（第 116 行“六个”改“七个”、R4 写明 13 个别名 + 1 个同签名包装），未改设计、owner 与契约。

## 审核状态

计划第 3 版为当前唯一计划。第 1 版结论 `NEEDS_MODIFICATION`（P1 两条、P2 一条、P4 一条）已按第 2 版修正并取得 `APPROVED`；第 3 版只按该轮的两条非阻断措辞把“六个函数”改为“七个”、“别名”改为“13 个别名 + 1 个同签名包装”，未改设计。后续审核以本文件、需求原文、`PROJECT_CONSENSUS.md` 与 `Plan Reviewer Rule.md` 为输入。
