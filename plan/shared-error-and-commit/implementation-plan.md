# 边界一：把共享错误通道与原子写／事务移入内部模块（执行计划）

## 版本、来源与状态

- 需求来源：负责人 2026-10-18 三批要求中的“其余边界”原文：

  > 共享错误通道、事务／回滚、Stage3 提交与校验交接、Stage4/5 证据处理：先按常规审核。移动时可能改变共享状态、异常类型或路径定位，不能仅保留旧函数名就认定等价。

- Requirement revision: 第 1 版（边界一：共享错误通道＋事务／回滚）。
- Canonical Plan revision: 第 2 版。
- Target repository revision: `b3972a2cdf5cd60a5bc6dea006c10cfb6516a3d6`（分支 `refactor/stage3-render-group`，已含批次二与批次三）。本批工作分支 `refactor/shared-error-and-commit` 从该提交拉出。
- Implementation sequencing prerequisite: PR #97（批次二）与 PR #98（批次三）尚未合并；本批堆叠在批次三之上，合并顺序 #97 → #98 → 本批。上游 PR 改写时，本批按受影响范围重放并重跑受影响检查。
- Relevant upstream/runtime revision: N/A；不涉及外部仓库、CLI、安装布局或代理入口。
- Proposed review status: pending。
- 唯一规范来源：本文件。本文件只定义实施方案，不声明计划审核、测试审核或合并关口已经通过。

## 正式需求与范围

- **R1 分组**：把 runner 的共享错误通道与原子写／事务两组能力移入一个内部模块，不按函数拆成多个 PR。
- **R2 通道语义不变**：`fail` 打印 `{"status": "error", ...}` 后以 1 退出；`soft_exit` 打印 `{"status": <status>, ...}` 后以 2 退出；`emit` 的 JSON 文本逐字节不变；业务通道开启时两者都改为抛 `ProfessorBusinessFailure`，不打印、不退出。
- **R3 异常类型不变**：`ProfessorBusinessFailure` 仍是同一个类对象，`except contact_state.ProfessorBusinessFailure` 仍能捕获；payload 结构不变。
- **R4 事务语义不变**：`atomic_write` 的写入内容与临时文件清理、`atomic_json` 的序列化格式、`atomic_json_many` 与 `staged_pair_commit` 的“先全部暂存、再逐个替换、失败按逆序回滚旧字节/删除新建文件”的行为不变；失败时抛出的异常类型与传播方式不变。
- **R5 调用面不变**：runner 内 600 多处调用点不改名、不改参；`contact_state.<name>` 仍是可用的模块级名字。

**非目标**：不改任何退出码、JSON 字段或业务判定；不改 `require_professor_dir_under_program` / `professor_dir_containment_error`（它们是路径守卫，不在本组）；不改 `managed_write` / `projection_write` / `managed_conflict`（受管文件语义，属另一组）；不改 Stage3 提交与校验交接、Stage4/5 证据处理；不改 CLI、安装布局或测试断言。

## 依据与关键事实

审核依据为项目 `PROJECT_CONSENSUS.md` 与 `Plan Reviewer Rule.md`；测试设计另按 `Test Engineer Rule.md` 审核。

| 决定 | 关键事实 | 来源（目标修订） |
| --- | --- | --- |
| 两组函数相邻成块 | `atomic_write` 209-223、`atomic_json` 226-227、`atomic_json_many` 230-277、`staged_pair_commit` 280-332、`emit` 335-336、`ProfessorBusinessFailure` 339-348、`_BUSINESS_CHANNEL` 351、`professor_business_channel` 354-364、`_business_channel_open` 367-368、`fail` 371-377、`soft_exit` 400-406 | `scripts/contact_state.py` |
| 调用面很大且只在 runner 内（docs 只有文字提及） | `fail` 522 处、`soft_exit` 52 处、`emit` 29 处、`atomic_write` 8 处、`atomic_json` 13 处、`atomic_json_many` 1 处、`staged_pair_commit` 1 处、`professor_business_channel` 1 处、`_business_channel_open` 2 处 | AST 统计（脚本见测试记录） |
| 组内自洽、无外部依赖 | 自由名字只有 `json`/`os`/`sys`/`tempfile`/`contextlib`/`Path`/`Any` 与组内互相引用（`fail`/`soft_exit` 用 `emit`、`_business_channel_open`、`ProfessorBusinessFailure`） | 同上 |
| 业务通道是进程内状态 | `_BUSINESS_CHANNEL` 是模块级 list，`professor_business_channel` 压栈/出栈，`fail`/`soft_exit` 读它决定“抛异常还是打印并退出” | `scripts/contact_state.py:351-368` |
| 退出码是正式契约 | `fail` → `sys.exit(1)`；`soft_exit` → `sys.exit(2)`；业务通道内改抛异常 | `scripts/contact_state.py:371-377`、`400-406` |
| 事务回滚语义 | `atomic_json_many` 先暂存全部、逐个 `os.replace`，失败时逆序恢复备份或删除已装文件；`staged_pair_commit` 先记旧字节、逐个替换，失败时逆序恢复旧字节或删除新建文件，最后一次安装是提交点 | `scripts/contact_state.py:230-332` |
| 故障注入按 `os.replace` 打 | issue67 的 `sitecustomize` 在子进程里替换 `os.replace` 制造安装失败，不依赖函数所在模块 | `tests/test_contact_state.py:3857-3880`（`ISSUE67_FAULT_SITECUSTOMIZE`） |
| 测试只有两处直接引用这两个组的名字 | `contact_state.atomic_json(...)`、`contact_state.staged_pair_commit([...])`；没有 patch、没有 `from contact_state import`、没有引用 `ProfessorBusinessFailure`/`_BUSINESS_CHANNEL` | 全仓测试检索 |
| 相邻模块的加载做法已在本仓成立 | `stage2_chatgpt_handoff.py` 与批次三的 `_stage3_render.py` 都用 `Path(__file__).with_name(...)` + `spec_from_file_location`；runner 可能被直接执行或被测试按路径加载，`scripts/` 不保证在 `sys.path` | `scripts/contact_state.py`（`_stage3_render` 加载块）、`scripts/stage2_chatgpt_handoff.py:41-51` |
| 两个夹具会复制 runner | 假安装布局夹具复制 runner 与 `_stage3_render.py`，新模块必须一并复制 | `tests/test_stage5_immutable.py:215-222`、`tests/test_stage5_dualtarget_contract.py:327-333` |

## 方案

### 因果链

需求（错误通道与原子写／事务继续留在巨型 runner 里）→ 现行机制（11 个名字在 runner 顶部成块，被 600 多处调用；业务通道用一个模块级 list 承载进程内状态；事务函数用 `tempfile.mkstemp` + `os.replace` 做原子替换与回滚）→ 变更点（按行区间原样搬入内部模块；runner 按既有做法按路径加载并把名字别名回自己的命名空间；两个复制 runner 的夹具同步复制新模块）→ 行为变化（用户可见的退出码、stdout JSON、文件写入与回滚完全不变；只是定义位置改变）→ 满足需求。

### 选定设计

**新模块 `scripts/_contact_io.py`**（下划线前缀沿用内部辅助模块约定）：文件头 `from __future__ import annotations` 与 `contextlib`/`json`/`os`/`sys`/`tempfile`/`Path`/`Any` 导入；以下 11 个名字按行区间**原样**搬入，不改签名、不改函数体：

- 事务／回滚：`atomic_write`、`atomic_json`、`atomic_json_many`、`staged_pair_commit`；
- 错误通道：`emit`、`ProfessorBusinessFailure`、`_BUSINESS_CHANNEL`、`professor_business_channel`、`_business_channel_open`、`fail`、`soft_exit`。

**runner 侧加载**：沿用 `_stage3_render` 的既有做法（`Path(__file__).with_name("_contact_io.py")`、`spec_from_file_location`、`module_from_spec`、`exec_module`；不改 `sys.path`、不注册 `sys.modules`），放在导入块之后、常量之前。

**runner 侧别名**：把 11 个名字显式别名回 runner 命名空间（`emit = _contact_io.emit` 等），因此 600 多处调用点、`except contact_state.ProfessorBusinessFailure` 与两个测试的直接调用都不变。别名是同一个对象，`contact_state.ProfessorBusinessFailure is _contact_io.ProfessorBusinessFailure` 为真。

**夹具同步**：两个把 runner 复制进假安装布局的夹具同时复制 `_contact_io.py`。

### 冻结的契约

- `fail` / `soft_exit` 的 stdout JSON 字段、`indent=1`、`sort_keys=True`、`ensure_ascii=False` 与退出码 1／2 不变；业务通道内改抛异常的行为不变。
- `ProfessorBusinessFailure` 的类对象在进程内唯一；payload 与 `args` 不变；别名后 `contact_state.ProfessorBusinessFailure` 与模块内是同一个对象。
- `emit` 的输出文本逐字节不变。
- `atomic_write` / `atomic_json` 的文件字节、`newline=""`、`fsync`、隐藏临时文件名模式（`.<name>.*`）与失败清理不变。
- `atomic_json_many` / `staged_pair_commit` 的暂存顺序、安装顺序、失败回滚顺序与异常传播不变；“最后一次安装是提交点”的语义不变。
- `_BUSINESS_CHANNEL` 的压栈／出栈与嵌套语义不变；一个模块实例对应一份通道状态，与今天一个 runner 实例对应一份的状态等价。
- 新模块缺失时 runner 在导入期以 `RuntimeError` 响亮失败（与 `_stage3_render` 同一形状），不会带着半套别名继续运行。
- `require_professor_dir_under_program`、`managed_write` 等调用方的名字与行为不变。

### 替代方向与取舍

| 方向 | 不采用的原因 |
| --- | --- |
| 拆成“错误通道”和“原子写”两个模块 | 两组都只依赖标准库、都在 runner 顶部、都被同一次搬移覆盖；拆两块会多一个加载器与一次别名清单，收益只是名义上的单一职责 |
| 新模块 import runner 取 `emit` 等 | 循环导入；runner 可能被按路径加载、模块名不一定在 `sys.modules` |
| 只搬函数体、把 `_BUSINESS_CHANNEL` 留在 runner | 通道状态与读写它的函数分离，反而制造跨模块共享状态 |
| 把业务通道改成 contextvar 或参数传递 | 改变并发/嵌套语义与调用面，超出“移动”范围 |
| 顺带搬 `require_professor_dir_under_program` / `managed_write` | 它们分别是路径守卫与受管文件语义，不属这两组；混做会扩大共享状态与异常面 |
| 让宿主模块把 `fail` 作为参数注入 | 600 多处调用点都要改，且调用面不再稳定 |

## 影响

- **intended_change**：错误通道与事务／回滚的实现移入 `_contact_io.py`；runner 以按路径加载 + 别名保持原调用面；两个复制夹具同步复制新模块。
- **preserved_behavior**：所有退出码与 stdout JSON；业务通道把失败转成 `ProfessorBusinessFailure`；`emit` 文本；原子写的文件字节与临时文件清理；两个事务函数的暂存／安装／回滚顺序与异常传播；issue67 的 `os.replace` 故障注入仍能命中；`contact_state.<name>` 全部可用。
- **approved_behavior_change**：无。定义位置变化，运行期没有已支持输入的行为变化。
- **prohibited_side_effect**：改变退出码或 JSON 字段；改变异常类型或把它包装成别的类；改变临时文件名模式、`fsync` 或回滚顺序；把 `_BUSINESS_CHANNEL` 变成跨 runner 实例共享；在 runner 里改 `sys.path`；顺带搬路径守卫或受管文件语义；改测试断言。
- **unresolved impact**：无影响方案成立的项目。仓库外若有人按脚本目录枚举文件会多看到一个内部模块，属预期新增文件；把 runner 复制到别处而不复制相邻模块的第三方脚本会加载失败——这一点在批次三已存在同一约束，本批只多一个模块。

## 关键安全条件与反例

必须一直成立的条件：

1. `fail` 与 `soft_exit` 在通道关闭时分别打印同样 JSON 并以 1／2 退出；在通道开启时都不打印、不退出，抛同一个 `ProfessorBusinessFailure` 类。
2. `contact_state.ProfessorBusinessFailure` 与模块内的类是同一个对象；`except contact_state.ProfessorBusinessFailure` 能捕获模块抛出的异常。
3. `atomic_write` 写出与今天逐字节相同的文件，成功后不留下 `.<name>.*` 临时文件；失败时清理临时文件并原样抛出。
4. `atomic_json_many` 与 `staged_pair_commit` 在中途失败时，把已安装文件恢复为旧字节、删除本次新建的文件，且按逆序处理。
5. `emit` 的输出与今天逐字节相同。
6. runner 无论以脚本方式执行、被测试按路径加载，还是被复制进假安装布局，都能按路径加载到 `_contact_io.py`。

代表性反例：

- 夹具只复制 runner：复制出的 runner 在导入阶段失败（由 T 覆盖）。
- 把 `ProfessorBusinessFailure` 改成在 runner 里重新定义：`except contact_state.ProfessorBusinessFailure` 将捕获不到模块抛出的异常，Stage4 逐教授失败行会变成进程退出——必须保持别名同一对象。
- 把 `_BUSINESS_CHANNEL` 改成模块间共享的全局单例：两个 runner 实例（测试里常见）会互相污染通道状态；必须保持“一个模块实例一份状态”。
- 用 `Path.write_text` 之类替代 `atomic_write`：会丢掉 `fsync`/`newline=""`/临时文件清理，回滚与 reader 可见性都会变。
- issue67 故障注入替换的是 `os.replace`：若把事务实现改成 `shutil.move` 或直接写目标文件，故障注入将不再命中，测试会以“未发生预期失败”暴露。

## 实施位置与顺序

1. **计划审核**：本文件取得 `Plan conclusion: APPROVED`。
2. **本地执行代理**（按获批计划实施）：
   - 新增 `scripts/_contact_io.py`：11 个名字按行区间原样搬入，补文件头导入。
   - `scripts/contact_state.py`：按上列行区间只删除这 11 个名字的定义（209-377 与 400-406），**保留 380-397 的两个路径守卫**——它们继续调用别名后的 `fail`；在导入块之后加按路径加载；用显式别名把 11 个名字放回 runner 命名空间；其余调用点不动。
   - `tests/test_stage5_immutable.py`、`tests/test_stage5_dualtarget_contract.py`：复制 runner 的夹具同时复制 `_contact_io.py`。
3. **测试准备与审核**：测试工程师按 `Test Engineer Rule.md` 准备测试资产（见同目录 `test-plan.md`）。
4. **正式执行**：测试计划获批后执行受影响测试并记录结果；未受影响的通过结果沿用。

## 修订记录

- 第 1 版：首次提交计划审核。
- 第 2 版：按第 1 轮审核的六条非阻断观察补全措辞——实施项写明只删除 11 个名字的定义、保留 380-397 两个路径守卫；事实行注明 docs 有文字提及；冻结契约补写新模块缺失时的导入期失败形状。方案、owner、冻结契约的其余内容与验证方式未变。

## 审核状态

计划第 2 版为当前唯一计划。第 1 版已取得 `Plan conclusion: APPROVED`（P1–P4 全 PASS）；第 2 版只落实该轮的非阻断措辞，未改方案、owner 与契约。后续审核以本文件、需求原文、`PROJECT_CONSENSUS.md` 与 `Plan Reviewer Rule.md` 为输入。
