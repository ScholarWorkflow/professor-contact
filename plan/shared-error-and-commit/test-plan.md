# 边界一：共享错误通道与原子写／事务移入内部模块（测试计划）

## 版本、来源与状态

- 对应执行计划：[implementation-plan.md](implementation-plan.md)，计划第 2 版。
- 需求来源：负责人 2026-10-18 授权的“其余边界”，原文见执行计划。
- 对照基准：`b3972a2cdf5cd60a5bc6dea006c10cfb6516a3d6`（本批从它拉出）。
- Target repository revision: 工作分支 `refactor/shared-error-and-commit` 实施后的提交。
- Test plan revision: 第 2 版。
- 测试范围依据：`Test Engineer Rule.md`。本清单是验收上限，只覆盖本批明确要保持的目标与本次直接改变的失败行为。
- Proposed review status: pending。

## 必测清单

| 编号 | 业务目标 | 输入 / 场景 | 预期结果 | 检查方式 |
| --- | --- | --- | --- | --- |
| T1 | 错误通道的退出码与 stdout 不变 | 同一驱动脚本分别加载基准修订与改动修订的 runner：调用 `emit`；在通道关闭时调用 `fail`、`soft_exit` | `emit` 输出文本逐字节相同；`fail` 的 stdout JSON 相同且退出码 1；`soft_exit` 的 stdout JSON 相同且退出码 2 | 仓库外驱动脚本，两次运行各输出一份规范化 JSON（stdout 文本 + 退出码），逐字段比较 |
| T2 | 业务通道仍把失败转成同一异常类型 | 驱动脚本进入 `professor_business_channel()` 后分别调用 `fail` 与 `soft_exit` | 两次都不打印、不退出；抛出的异常类型名与 payload 相同；`type(exc) is contact_state.ProfessorBusinessFailure` 为真；通道关闭后行为回到 T1 | 同 T1 驱动脚本 |
| T3 | 原子写与两个事务的回滚行为不变 | 驱动脚本在各自临时目录里：`atomic_write` 写文本；`atomic_json` 写对象；`atomic_json_many` 成功一次、**安装期**失败一次；`staged_pair_commit` 成功一次、**安装期**失败一次。安装期失败用临时替换 `os.replace`、只在第二次调用时抛 `OSError` 制造：`atomic_json_many` 此时首个文件已建立备份、`staged_pair_commit` 此时首个文件已安装，因此都会走到回滚分支 | 成功时文件字节与今天相同、无 `.<name>.*` 残留；失败时已安装文件恢复旧字节、未安装文件保持原样、无残留、异常类型与 `os.replace` 调用次数相同 | 同 T1 驱动脚本（只打印相对路径与内容，避免临时目录前缀差异）；`os.replace` 在 `finally` 恢复 |
| T4 | 既有业务路径不受影响 | 逐教授失败行（Stage 4 finalize，`professor_business_channel` 把异常转成该教授的 result row）、Stage 3 本地事务提交、issue67 的 `os.replace` 故障注入（`stage4-migrate-local` / 相邻状态路径）、Stage 3 的 `soft_exit` 转 row | 全部通过 | 逐教授失败行与 `soft_exit` 转 row 由 `test_issue67_gate2_r3`、`test_stage3_direction_groups` 覆盖；故障注入与迁移路径由 `test_contact_state.Issue67ProfessorLocalStage4Tests`、`test_contact_state.Issue67AdjacentStateTests` 覆盖；Stage 3 本地事务提交由 `test_issue66_stage3_local_state` 覆盖；另跑 `test_stage4_selection_agent_contract`、`test_stage3_stage4_caller_contract` 两个合同文件（它们只断言正文文本，不承担上述运行时覆盖） |
| T5 | 未改动区域的既有门禁 | 仓库 CI 对 PR 提交跑全量 `unittest discover` | 全量通过 | 直接引用 PR 的 CI 运行结果，不在本地重复全仓回归 |

## 执行步骤

准备与执行都在工作树 `/Users/rekidunois/code/skill-repos-dev/worktrees/refactor-shared-error-and-commit` 内进行；驱动脚本与运行产物放仓库外 `/tmp`（本次用 `mktemp -d /tmp/pc-bnd1-XXXXXX`）。

1. 准备：确认工作树只有本批改动、Python 可用，并取出基准修订的 Runner 副本。
   ```sh
   cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-shared-error-and-commit
   git status --porcelain
   python3 --version
   RUN=$(mktemp -d /tmp/pc-bnd1-XXXXXX)
   git show b3972a2cdf5cd60a5bc6dea006c10cfb6516a3d6:.apm/skills/professor-contact/scripts/contact_state.py > "$RUN/base_contact_state.py"
   git show b3972a2cdf5cd60a5bc6dea006c10cfb6516a3d6:.apm/skills/professor-contact/scripts/_stage3_render.py > "$RUN/_stage3_render.py"
   ```
   第二条是必须的：基准修订已含批次三，runner 在导入期就按 `Path(__file__).with_name("_stage3_render.py")` 加载兄弟模块；只放 `contact_state.py` 会在加载基线时 `FileNotFoundError`。工作树侧的 runner 兄弟模块在原位，无需处理。
2. T1、T2、T3：分别以基准 runner 与工作树 runner 为参数运行同一驱动脚本，各产出一份规范化结果，再比较。
   ```sh
   uv run --no-project "$RUN/contract_probe.py" "$RUN/base_contact_state.py" "$RUN/base-work" > "$RUN/base.json"
   uv run --no-project "$RUN/contract_probe.py" .apm/skills/professor-contact/scripts/contact_state.py "$RUN/head-work" > "$RUN/head.json"
   diff -u "$RUN/base.json" "$RUN/head.json" && echo "T1-T3 IDENTICAL"
   ```
   预期：`diff` 无输出并打印 `T1-T3 IDENTICAL`。
3. T4：既有业务用例。
   ```sh
   cd .apm/skills/professor-contact/tests
   python3 -m unittest test_stage4_selection_agent_contract test_stage3_stage4_caller_contract \
     test_issue66_stage3_local_state test_issue67_gate2_r3 test_stage3_direction_groups \
     test_contact_state.Issue67ProfessorLocalStage4Tests test_contact_state.Issue67AdjacentStateTests -v
   ```
   预期：全部 `ok`，无 `FAIL`/`ERROR`。
4. T5：把改动推送到 PR 后引用仓库 CI 的全量结果；CI 未通过时按第 6 步处理。
5. 记录：保存命令、实际提交 SHA、逐项结果与必要输出片段到 `/tmp` 运行目录，并把方法与结果写入 `test-execution-<日期>.md`。
6. 失败处理：
   - T1–T3 出现差异：按差异定位到具体函数与字段，判定为产品缺陷交实现负责人修正后重跑 T1–T3。
   - 既有用例失败：区分“本次引入”“既有失败”“环境问题”；本次引入的回归修正后重跑受影响编号。
   - 既有跳过项按未执行记录，不算失败；不做无新信息的重复运行。

## 驱动脚本要点（T1–T3）

- 用 `importlib.util.spec_from_file_location` 按路径加载传入的 runner，模块名带唯一后缀，两次运行互不共享 `sys.modules`。
- 所有路径都相对传入的工作目录，输出只含相对路径与文件内容；两份结果因此可以直接 `diff`。
- 用 `contextlib.redirect_stdout(io.StringIO())` 捕获 `emit`/`fail`/`soft_exit` 的 stdout 文本，用 `try/except SystemExit` 记录退出码。
- 业务通道：`with runner.professor_business_channel():` 内分别调用 `fail` 与 `soft_exit`（两次独立的通道块），捕获 `runner.ProfessorBusinessFailure`，记录 `type(exc).__name__`、`exc.payload`、`str(exc)`、捕获到的 stdout 与 `type(exc) is runner.ProfessorBusinessFailure`。
- 事务失败注入：临时替换 `os.replace`，只在第二次调用时抛 `OSError`（安装期失败），并在 `finally` 恢复；记录失败后每个文件的存在性与字节、异常类型与 `os.replace` 调用次数。**不要**用“父路径是普通文件”制造失败——那会在暂存期抛错、回滚分支为空，等于没有覆盖回滚。
- 成功场景：`atomic_json_many` 与 `staged_pair_commit` 各跑一次成功用例，记录文件字节，并列出工作目录里所有以 `.` 开头的残留临时文件（预期为空）。
- 断言：两份 JSON 的 `emit`、`fail`、`soft_exit`、`business`、`atomic`、`json`、`json_many`、`pair_commit` 各键逐字段相等。

## 环境与预检

- 使用仓库现有的本地 Python（本次准备时记录 `python3 --version` 实际值）与既有测试夹具；驱动脚本只用标准库。
- 测试只使用合成数据与临时目录；不接触用户业务资料；`PROFESSOR_CONTACT_EVIDENCE_SCRIPT` 由既有夹具自行恢复，本批不新增环境变量。
- 预检只确认命令可用、工作树状态、基准 runner 能取出；不预先执行业务目标命令求结果。

## 不纳入本清单的范围

| 未纳入项 | 原因 |
| --- | --- |
| 共享错误通道与事务函数在新模块里的独立单元测试 | 属于内部组织；T1–T3 已用基准修订对照直接验证语义 |
| `managed_write` / `projection_write` / `require_professor_dir_under_program` | 本批不动这些函数 |
| 全仓本地回归 | 仓库 CI 已在 PR 上执行全量 discover，按 `Test Engineer Rule.md` 第 6 节直接引用 |
| Stage3 提交与校验交接、Stage4/5 证据处理 | 属另外的常规审核 PR |

## 修订记录

- 第 1 版：首次提交测试计划审核。
- 第 2 版：按第一、二关口的三个 blocker 修正——B1 把 T3 的失败注入从“暂存期 mkdir 失败”改为“安装期第二次 `os.replace` 抛错”，并写明判据；B2 第 1 步补取基准修订的 `_stage3_render.py`；B3 把 T4 的检查入口与命令对齐（加入 `test_stage3_direction_groups` 与 `test_contact_state` 的两个 Issue67 运行时类，并说明两个合同文件不承担运行时覆盖）。同时按非阻断意见在驱动里补通道内 `soft_exit` 与 `atomic_json_many` 成功用例、更新执行计划版本指针。

## 审核状态

测试计划第 2 版为当前唯一版本。第 1 版的三个 blocker 已在本版修正，业务目标与必测编号未变。后续审核以本文件、执行计划与 `Test Engineer Rule.md` 为输入。
