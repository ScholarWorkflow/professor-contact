# 边界一：共享错误通道与原子写／事务搬移 测试执行记录（2026-10-19）

- 测试计划：[test-plan.md](test-plan.md)，第 1 版。
- 执行计划：[implementation-plan.md](implementation-plan.md)，第 2 版（`Plan conclusion: APPROVED`，P1–P4 全 PASS）。
- 对照基准：`b3972a2cdf5cd60a5bc6dea006c10cfb6516a3d6`（本批从它拉出）。
- 被测提交：`98f429c4dd41c89d1fdfcd14024cf8313c37d7bd`；执行时 `git status --porcelain` 为空。
- 环境：本地 macOS，Python 3.14.7；只使用标准库与既有夹具。仓库 CI 使用工作流固定的 Python 3.12。
- 原始输出（仓库外）：`/tmp/pc-bnd1-*/`；本文件只记录命令、方法与结果。

## 逐项结果

| 编号 | 结果 | 证据 |
| --- | --- | --- |
| T1 | 通过 | 基准与改动后的 runner 各跑一次驱动脚本，`diff -u` 无输出（`T1-T3 IDENTICAL`）；`emit` 文本、`fail` 的 stdout JSON 与退出码 1、`soft_exit` 的 stdout JSON 与退出码 2 逐字段相同 |
| T2 | 通过 | 同一对比：业务通道内 `fail` 不打印、不退出，异常类型名、`payload`、`args` 相同，`type(exc) is runner.ProfessorBusinessFailure` 为真；退出通道后 `fail` 回到“打印 + 退出 1” |
| T3 | 通过 | 同一对比：`atomic_write`／`atomic_json` 的文件字节与无临时残留相同；`atomic_json_many` 与 `staged_pair_commit` 在注入的第二次 `os.replace` 失败后，文件恢复旧字节、无 `.name.*` 残留、`replace` 调用次数与异常类型相同 |
| T4 | 通过 | `Ran 56 tests in 51.848s`，`OK`，退出码 0 |
| T5 | 通过 | 仓库 CI 在 PR 提交上跑全量 `unittest discover`，检查项 `test` 通过（见 PR 检查项） |

## 执行方法与命令

1. 取出基准修订的 runner 与它依赖的相邻模块到仓库外目录：

   ```sh
   RUN=$(mktemp -d /tmp/pc-bnd1-XXXXXX)
   git show b3972a2cdf5cd60a5bc6dea006c10cfb6516a3d6:.apm/skills/professor-contact/scripts/contact_state.py > "$RUN/base_contact_state.py"
   git show b3972a2cdf5cd60a5bc6dea006c10cfb6516a3d6:.apm/skills/professor-contact/scripts/_stage3_render.py > "$RUN/_stage3_render.py"
   ```

2. T1–T3：同一驱动脚本分别以基准 runner 与工作树 runner 为参数运行，各产出一份规范化 JSON：

   ```sh
   uv run --no-project "$RUN/contract_probe.py" "$RUN/base_contact_state.py" "$RUN/base-work2" > "$RUN/base2.json"
   uv run --no-project "$RUN/contract_probe.py" .apm/skills/professor-contact/scripts/contact_state.py "$RUN/head-work2" > "$RUN/head2.json"
   diff -u "$RUN/base2.json" "$RUN/head2.json"
   ```

   驱动脚本用 `contextlib.redirect_stdout` 捕获输出、`try/except SystemExit` 记录退出码；业务通道用 `with runner.professor_business_channel()` 包裹；事务失败通过临时替换 `os.replace`（只在第二次调用时抛 `OSError`）制造，并在 `finally` 恢复；所有路径都相对各自工作目录输出。

3. T4：既有业务用例。

   ```sh
   cd .apm/skills/professor-contact/tests
   python3 -m unittest test_stage4_selection_agent_contract test_stage3_stage4_caller_contract \
     test_issue66_stage3_local_state test_issue67_gate2_r3 -v
   ```

4. 搬移核对：`git show` 取基准修订的 209-377 与 400-406 行，与新模块正文 `diff -u` 无输出（178 行逐字一致）。

## 执行中修正的两处测试资产问题（保留记录）

- 首次运行基准侧失败：基准 runner 的 `_stage3_render.py` 没有一并放到 `/tmp`，驱动脚本在导入期报 `FileNotFoundError`。补上该相邻模块后重跑通过；属准备步骤缺项，不是产品问题。
- `atomic_json_many` 的中途失败最初用“第二个目标父路径是普通文件”制造，失败发生在暂存阶段（`replace` 调用 0 次），没有覆盖安装期回滚。改为“第二次 `os.replace` 抛错”后，两个事务函数都覆盖到“已安装一项后失败并回滚”的路径。

## 兼容性门禁

- 仓库 CI（`.github/workflows/ci.yml`）在本 PR 提交上运行全量 `python -m unittest discover -s .apm/skills/professor-contact/tests -p 'test_*.py' -v`；结果见 PR 检查项，本批不在本地重复全仓回归。

## 结论与交接

- T1–T4 对被测提交 `98f429c` 全部取得通过结果；T5 以 PR CI 结果为准。
- 本记录之后如只改文档，未改产品与测试代码时，上述逐项结果继续有效并沿用。
- 依赖顺序：本批堆叠在批次三分支 `refactor/stage3-render-group`（PR #98）之上，合并顺序 #97 → #98 → 本批。
- 下一负责人：测试计划审核（第一、二关口）、第三关口与合并审核；本记录不代替任何关口结论。
