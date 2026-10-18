# 边界一：共享错误通道与原子写／事务搬移 测试执行记录（2026-10-19）

- 测试计划：[test-plan.md](test-plan.md)，第 5 版。
- 执行计划：[implementation-plan.md](implementation-plan.md)，第 2 版（`Plan conclusion: APPROVED`，P1–P4 全 PASS）。
- 对照基准：`b3972a2cdf5cd60a5bc6dea006c10cfb6516a3d6`（本批从它拉出）。
- 被测提交：`98f429c4dd41c89d1fdfcd14024cf8313c37d7bd`；执行时 `git status --porcelain` 为空。
- 环境：本地 macOS，Python 3.14.7；只使用标准库与既有夹具。仓库 CI 使用工作流固定的 Python 3.12。
- 原始输出（仓库外）：`/tmp/pc-bnd1-DyNATS/`（本轮实际目录，点名到目录而非通配）；本文件只记录命令、方法与结果。

## 逐项结果

| 编号 | 结果 | 证据 |
| --- | --- | --- |
| T1 | 通过 | 基准与改动后的 runner 各跑一次驱动脚本，`diff -u` 无输出（`T1-T3 IDENTICAL`）；`emit` 文本、`fail` 的 stdout JSON 与退出码 1、`soft_exit` 的 stdout JSON 与退出码 2 逐字段相同 |
| T2 | 通过 | 同一对比：业务通道内 `fail` 与 `soft_exit` 都不打印、不退出，异常类型名、`payload`、`args` 相同，`type(exc) is runner.ProfessorBusinessFailure` 为真；退出通道后 `fail` 回到“打印 + 退出 1” |
| T3 | 通过 | 同一对比：`atomic_write`／`atomic_json` 的文件字节与无临时残留相同；`atomic_json_many` 成功写入两个文件；失败注入按第 3 版计划改到**第四次** `os.replace`（两个目标都预先存在：备份一 → 安装一 → 备份二 → 安装二），两侧均为 `OSError`、`replace` 调用 6 次、文件一从已安装的新内容回滚为旧字节、文件二保持旧内容、无残留；`staged_pair_commit` 仍在第二次替换（文件一已安装）注入，两侧均为 `OSError`、3 次调用、`t1` 回 `OLD-A`、`t2` 保持 `OLD-B` |
| T4 | 通过 | 按第 5 版清单只跑 5 个方法：`Ran 5 tests in 7.842s`，`OK`，退出码 0。更早的 `Ran 95 tests in 122.572s` 是这 5 项的超集，保留作历史证据；其中多出的部分（两个只断言文档文本的合同文件、三个模块的其余用例、issue #67 归属类用例）不作为本批通过条件 |
| 既有仓库检查 | 通过 | 仓库 CI 在 head `1a62d0d` 上跑全量 `unittest discover`：运行 `39147234123`，8m7s，检查项 `test` pass。按测试计划第 4 版，这项不属于本批业务必测项，只作既有检查结果引用；该 head 相对被测提交只多文档提交，`.apm/` 字节未变 |

## 执行方法与命令

1. 取出基准修订的 runner 与它依赖的相邻模块到仓库外目录：

   ```sh
   set -e
   RUN=/tmp/pc-bnd1-DyNATS           # 本轮实际运行目录；驱动已在该目录，换新目录时按计划第 1 步 cp 过去
   test -f "$RUN/contract_probe.py"
   git show b3972a2cdf5cd60a5bc6dea006c10cfb6516a3d6:.apm/skills/professor-contact/scripts/contact_state.py > "$RUN/base_contact_state.py"
   git show b3972a2cdf5cd60a5bc6dea006c10cfb6516a3d6:.apm/skills/professor-contact/scripts/_stage3_render.py > "$RUN/_stage3_render.py"
   ```

2. T1–T3：同一驱动脚本分别以基准 runner 与工作树 runner 为参数运行，各产出一份规范化 JSON：

   ```sh
   set -e
   uv run --no-project "$RUN/contract_probe.py" "$RUN/base_contact_state.py" "$RUN/base-work" > "$RUN/base.json"
   uv run --no-project "$RUN/contract_probe.py" .apm/skills/professor-contact/scripts/contact_state.py "$RUN/head-work" > "$RUN/head.json"
   diff -u "$RUN/base.json" "$RUN/head.json" && echo "T1-T3 IDENTICAL"
   ```

   注入修正（`atomic_json_many` 改注入第四次替换）后，用同一条命令换输出名重跑一次，最终证据是 `base5.json`／`head5.json`（`replace_calls: 6`）；更早的 `base4.json`／`head4.json`（第二次注入，`replace_calls: 3`）只作历史尝试保留。

   **最终证据是注入修正后重跑的 `base5.json`／`head5.json`（`atomic_json_many` 在第四次 `os.replace` 注入），T1–T3 三行以它为准；`base4.json`／`head4.json` 是第二次注入版本的运行，保留作历史尝试（`replace_calls: 3`）。** 更早的 `base2.json`／`head2.json`（10 个键，驱动扩展前）只作历史尝试保留，不作为结论依据。

   驱动脚本用 `contextlib.redirect_stdout` 捕获输出、`try/except SystemExit` 记录退出码；业务通道用 `with runner.professor_business_channel()` 包裹；事务失败通过临时替换 `os.replace` 制造（`atomic_json_many` 注入第四次、`staged_pair_commit` 注入第二次），并在 `finally` 恢复；所有路径都相对各自工作目录输出。

3. T4：只跑清单列出的 5 个方法（第 4/5 版收窄后的命令）。

   ```sh
   set -e
   cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-shared-error-and-commit/.apm/skills/professor-contact/tests
   python3 -m unittest \
     test_issue66_stage3_local_state.Issue66LocalStateTests.test_local_finalize_restores_both_files_when_state_install_fails \
     test_issue66_stage3_local_state.Issue66LocalStateTests.test_staged_pair_keeps_committed_files_when_cleanup_fails \
     test_contact_state.Issue67ProfessorLocalStage4Tests.test_03_second_file_install_failure_rolls_the_pair_back \
     test_contact_state.Issue67ProfessorLocalStage4Tests.test_12_fatal_after_a_commit_keeps_a_and_fresh_retry_uses_current_facts \
     test_contact_state.Issue67AdjacentStateTests.test_05_fatal_run_without_aggregate_success_gives_the_caller_nothing \
     -v
   ```

4. 搬移核对：`git show` 取基准修订的 209-377 与 400-406 行，与新模块正文 `diff -u` 无输出（178 行逐字一致）。

## 执行中修正的两处测试资产问题（保留记录）

- 首次运行基准侧失败：基准 runner 的 `_stage3_render.py` 没有一并放到 `/tmp`，驱动脚本在导入期报 `FileNotFoundError`。补上该相邻模块后重跑通过；属准备步骤缺项，不是产品问题。
- `atomic_json_many` 的中途失败最初用“第二个目标父路径是普通文件”制造，失败发生在暂存阶段（`replace` 调用 0 次），没有覆盖安装期回滚。改为“第二次 `os.replace` 抛错”后，两个事务函数都覆盖到“首个文件已建立备份／已安装后失败并回滚”的路径；测试计划第 2 版已把注入方式与判据改写成与该执行一致。
- 一次驱动脚本改动（补通道内 `soft_exit` 与 `atomic_json_many` 成功用例）曾把成功用例插在 `handle` 定义之前，两次运行都以 `NameError` 退出；修正位置后重跑，两侧仍逐字段相同。该失败尝试保留在 `/tmp/pc-bnd1-*/base3.json`、`head3.json` 与对应 `.err` 中。
- 第 3 版审核（测试计划当时的版本号）指出 `atomic_json_many` 只注入第二次替换无法证明“已安装后回滚”；驱动改为在第四次替换注入（两个目标都预先存在）后重跑，两侧仍逐字段相同，文件一确实从已安装的新内容回滚为旧字节（`replace_calls: 6`）。旧注入的运行保留在 `/tmp/pc-bnd1-*/base4.json`、`head4.json`。
- 更早两次失败尝试只有文字描述（首次因基准缺 `_stage3_render.py` 导入失败；第二次用“父路径是普通文件”注入、只走到暂存期），其原始 JSON 未单独归档；第三次（`NameError`）留有产物。按 `Test Engineer Rule.md` 第 6 节，属已有记录与路径范畴，不重跑。
- T4 的命令最初只跑四个文件，未包含承载 issue67 故障注入与 `stage4-migrate-local` 的运行时类；测试计划第 2 版把命令与检查入口对齐后重跑，95 个用例通过。

## 兼容性门禁

- 仓库 CI（`.github/workflows/ci.yml`）在本 PR 提交上运行全量 `python -m unittest discover -s .apm/skills/professor-contact/tests -p 'test_*.py' -v`；结果见 PR 检查项，本批不在本地重复全仓回归。

## 结论与交接

- T1–T4 对被测提交 `98f429c` 取得有效通过结果（定向重跑时的 head 为 `1a62d0d`，此后只有文档提交）；仓库 CI 作为既有检查单独引用。
- 本记录之后如只改文档，未改产品与测试代码时，上述逐项结果继续有效并沿用。
- 依赖顺序：本批堆叠在批次三分支 `refactor/stage3-render-group`（PR #98）之上，合并顺序 #97 → #98 → 本批。
- 下一负责人：测试计划审核（第一、二关口）、第三关口与合并审核；本记录不代替任何关口结论。
