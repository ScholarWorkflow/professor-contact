# 边界一：共享错误通道与原子写／事务移入内部模块（测试计划）

## 版本、来源与状态

- 对应执行计划：[implementation-plan.md](implementation-plan.md)，计划第 2 版。
- 需求来源：负责人 2026-10-18 授权的“其余边界”，原文见执行计划。
- 对照基准：`b3972a2cdf5cd60a5bc6dea006c10cfb6516a3d6`（本批从它拉出）。
- Target repository revision: 工作分支 `refactor/shared-error-and-commit` 实施后的提交。
- Test plan revision: 第 6 版。
- 测试范围依据：`Test Engineer Rule.md`。本清单是验收上限，只覆盖本批明确要保持的目标与本次直接改变的失败行为。
- Proposed review status: pending。

## 必测清单

| 编号 | 业务目标 | 输入 / 场景 | 预期结果 | 检查方式 |
| --- | --- | --- | --- | --- |
| T1 | 错误通道的退出码与 stdout 不变 | 同一驱动脚本分别加载基准修订与改动修订的 runner：调用 `emit`；在通道关闭时调用 `fail`、`soft_exit` | `emit` 输出文本逐字节相同；`fail` 的 stdout JSON 相同且退出码 1；`soft_exit` 的 stdout JSON 相同且退出码 2 | 仓库外驱动脚本，两次运行各输出一份规范化 JSON（stdout 文本 + 退出码），逐字段比较 |
| T2 | 业务通道仍把失败转成同一异常类型 | 驱动脚本进入 `professor_business_channel()` 后分别调用 `fail` 与 `soft_exit` | 两次都不打印、不退出；抛出的异常类型名与 payload 相同；`type(exc) is contact_state.ProfessorBusinessFailure` 为真；通道关闭后行为回到 T1 | 同 T1 驱动脚本 |
| T3 | 原子写与两个事务的回滚行为不变 | 驱动脚本在各自临时目录里：`atomic_write` 写文本；`atomic_json` 写对象；`atomic_json_many` 成功一次、**部分安装后**失败一次；`staged_pair_commit` 成功一次、**首个文件安装后**失败一次。两个目标都预先存在时，`atomic_json_many` 的替换顺序是「备份文件一 → 安装文件一 → 备份文件二 → 安装文件二」，注入点是**第四次** `os.replace`（此时文件一已完整安装为新内容）；`staged_pair_commit` 的注入点是第二次（文件一已安装） | 成功时文件字节与今天相同、无 `.<name>.*` 残留；失败时已安装的新文件被删除并恢复旧字节、第二个文件保持旧内容、无残留、异常类型与 `os.replace` 调用次数相同 | 同 T1 驱动脚本（只打印相对路径与内容，避免临时目录前缀差异）；`os.replace` 在 `finally` 恢复。只注入第二次替换无法证明 `atomic_json_many` 的“已安装后回滚”，不要退回该写法 |
| T4 | 既有业务路径不受影响（只选**以本批行为为主要目的**的方法） | ① 事务回滚与提交点：`test_issue66_stage3_local_state.Issue66LocalStateTests.test_local_finalize_restores_both_files_when_state_install_fails`、`test_staged_pair_keeps_committed_files_when_cleanup_fails`；② `os.replace` 故障注入（`staged_pair_commit` 的安装失败与回滚）：`test_contact_state.Issue67ProfessorLocalStage4Tests.test_03_second_file_install_failure_rolls_the_pair_back` | 3 个方法全部通过（实测 `Ran 3 tests in 3.500s`） | 只运行这 3 个方法（见第 3 步命令）。业务通道把失败转成 result row 的行为由 T2 的驱动直接覆盖（通道内 `fail`/`soft_exit` 抛同一异常、通道外回到打印+退出）。按第 5 版审核的 B1 移出两个方法：`test_12_fatal_after_a_commit_keeps_a_and_fresh_retry_uses_current_facts`（还要求重跑时读取更新后的事实与历史数据，属 Stage 4 的其它规则）与 `test_05_fatal_run_without_aggregate_success_gives_the_caller_nothing`（与 `test_03_second_file_install_failure_rolls_the_pair_back` 重复设置同一行为的通过条件）。`test_issue66_stage3_local_state` 其余 4 项、`test_issue67_gate2_r3` 全部 6 项、`test_stage3_direction_groups` 全部 19 项都不以本批行为为主要目的，不作为通过条件 |

**既有仓库检查（不属于本批业务必测清单）**：仓库 CI 的全量 `unittest discover` 由仓库工作流照常执行，其结果单独引用，不作为本批业务必测项，也不因本批而扩张或缩减；合并要求继续按仓库规则执行。

## 执行步骤

准备与执行都在工作树 `/Users/rekidunois/code/skill-repos-dev/worktrees/refactor-shared-error-and-commit` 内进行；驱动脚本与运行产物放仓库外 `/tmp`（本次用 `mktemp -d /tmp/pc-bnd1-XXXXXX`）。

1. 准备：确认工作树只有本批改动、Python 可用，取出基准修订的 Runner 与兄弟模块，并把上一轮实际使用的驱动脚本复制进本轮目录。
   ```sh
   set -e
   cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-shared-error-and-commit
   git status --porcelain
   python3 --version
   RUN=$(mktemp -d /tmp/pc-bnd1-XXXXXX)
   git show b3972a2cdf5cd60a5bc6dea006c10cfb6516a3d6:.apm/skills/professor-contact/scripts/contact_state.py > "$RUN/base_contact_state.py"
   git show b3972a2cdf5cd60a5bc6dea006c10cfb6516a3d6:.apm/skills/professor-contact/scripts/_stage3_render.py > "$RUN/_stage3_render.py"
   cp /tmp/pc-bnd1-DyNATS/contract_probe.py "$RUN/contract_probe.py"
   ```
   末条是必须的：驱动自带输入构造与断言；来源缺失时按执行记录里记录的该轮目录找回同一脚本，仍找不到就停止并交计划所有人，不得凭提纲重写比较方法。
   第二条是必须的：基准修订已含批次三，runner 在导入期就按 `Path(__file__).with_name("_stage3_render.py")` 加载兄弟模块；只放 `contact_state.py` 会在加载基线时 `FileNotFoundError`。工作树侧的 runner 兄弟模块在原位，无需处理。
2. T1、T2、T3：分别以基准 runner 与工作树 runner 为参数运行同一驱动脚本，各产出一份规范化结果，再比较。`set -e` 保证任一侧运行失败立即中止，不会出现“两侧都失败、输出都为空、`diff` 仍然成功”的假结论。
   ```sh
   set -e
   uv run --no-project "$RUN/contract_probe.py" "$RUN/base_contact_state.py" "$RUN/base-work" > "$RUN/base.json"
   uv run --no-project "$RUN/contract_probe.py" .apm/skills/professor-contact/scripts/contact_state.py "$RUN/head-work" > "$RUN/head.json"
   diff -u "$RUN/base.json" "$RUN/head.json" && echo "T1-T3 IDENTICAL"
   ```
   预期：两条驱动命令都退出 0（否则 `set -e` 立即中止），`diff` 无输出并打印 `T1-T3 IDENTICAL`。
3. T4：只跑清单列出的 3 个方法（第 6 版收窄后的命令）。
   ```sh
   set -e
   cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-shared-error-and-commit/.apm/skills/professor-contact/tests
   python3 -m unittest \
     test_issue66_stage3_local_state.Issue66LocalStateTests.test_local_finalize_restores_both_files_when_state_install_fails \
     test_issue66_stage3_local_state.Issue66LocalStateTests.test_staged_pair_keeps_committed_files_when_cleanup_fails \
     test_contact_state.Issue67ProfessorLocalStage4Tests.test_03_second_file_install_failure_rolls_the_pair_back \
     -v
   ```
   预期：`Ran 3 tests`、全部 `ok`（在 head 上实测 `Ran 3 tests in 3.500s`）。此前的 5 项与 95 项运行都是本次命令的超集（含两个只断言文档文本的合同文件、`test_contact_state` 两个类的其余 17 项，以及三个模块的其余用例），多出的部分不构成本批通过条件，也不要求删除测试文件；两个被移出的方法按第 5 版审核的 B1 只作历史事实保留。
4. 既有仓库检查：把改动推送到 PR 后引用仓库 CI 的全量结果（不属于本批必测项）；CI 未通过时按第 6 步处理。
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
- 事务失败注入：临时替换 `os.replace` 并在 `finally` 恢复。**`atomic_json_many` 注入第四次调用**（两个目标都预先存在时序列为「备份一 → 安装一 → 备份二 → 安装二」，第四次失败时文件一已完整安装为新内容）；**`staged_pair_commit` 注入第二次调用**（文件一已安装）。记录失败后每个文件的存在性与字节、异常类型与 `os.replace` 调用次数。**不要**用“父路径是普通文件”制造失败（那会在暂存期抛错、回滚分支为空），也不要退回“只注入第二次”的写法（`atomic_json_many` 此时尚未安装任何新文件，证明不了部分安装后的回滚）。
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

## 自检

提交审核前逐条核对（与共用清单 `plan/test-plan-checklist.md` 同一口径；该清单随 PR #98 引入，本分支不把它当作已存在的文件）：① 必测项只引用能证明本批行为的方法；② CI 不在必测清单；③ 每个临时脚本都有确切来源与复制命令；④ 命令块启用 `set -e`；⑤ 失败注入到达目标分支；⑥ 计划文字与执行记录用同一套标签；⑦ 编号与版本一致。

## 修订记录

- 第 1 版：首次提交测试计划审核。
- 第 2 版：按第一、二关口的三个 blocker 修正——B1 把 T3 的失败注入从“暂存期 mkdir 失败”改为“安装期第二次 `os.replace` 抛错”，并写明判据；B2 第 1 步补取基准修订的 `_stage3_render.py`；B3 把 T4 的检查入口与命令对齐（加入 `test_stage3_direction_groups` 与 `test_contact_state` 的两个 Issue67 运行时类，并说明两个合同文件不承担运行时覆盖）。同时按非阻断意见在驱动里补通道内 `soft_exit` 与 `atomic_json_many` 成功用例、更新执行计划版本指针。
- 第 3 版：按第 2 版审核的四个 blocker 修正——B1 第 1 步补 `cp` 复制驱动脚本的明确命令与缺失时的处理；B2 第 2 步启用 `set -e` 并要求两条驱动命令都成功后才比较；B3 `atomic_json_many` 的注入点从第二次 `os.replace` 改为第四次（两个目标都预先存在时此时文件一已完整安装），`staged_pair_commit` 保持第二次；B4 把仓库 CI 移出业务必测清单改为“既有仓库检查”，并从 T4 命令移除只断言文档文本的两个合同文件。
- 第 4 版：按负责人“同一类问题要一次清干净”的要求再收窄 T4——从“三个整模块 + 两个类”改为**7 个以本批行为为主要目的的方法**（事务回滚/提交点 2、`os.replace` 故障注入 3、业务通道转 result row 2），并在行内写明被排除的同文件用例与理由。
- 第 5 版：按独立审查把剩下的 2 个 issue #67 归属类用例也移出 T4（业务通道转 row 由 T2 驱动直接覆盖），T4 定为 5 个方法，并写明被排除文件的理由。
- 第 6 版：按第 5 版审核的 B1 再移出两个方法——`test_12_fatal_after_a_commit_keeps_a_and_fresh_retry_uses_current_facts`（含 Stage 4 其它规则）与 `test_05_fatal_run_without_aggregate_success_gives_the_caller_nothing`（与 `test_03_...` 重复），T4 定为 3 个方法；执行记录同步更新，5 项与 95 项运行保留为历史事实。

## 审核状态

测试计划第 6 版为当前唯一版本。第 5 版结论 NEEDS_MODIFICATION（B1），已按上节修正。第 1 版的三个 blocker 已按第 2 版修正；第 3 版按第 2 版审核的四个 blocker 修正范围、步骤与注入点（必测编号由 T1–T5 收为 T1–T4、仓库 CI 移出必测清单）；第 4 版把 T4 收窄为 7 个具体方法；第 5 版按独立审查再收窄为 5 个（移出两个 issue #67 归属类用例）。后续审核以本文件、执行计划与 `Test Engineer Rule.md` 为输入。
