# Stage 2 划分第三批：resolve 提交层（测试计划）

## 版本、来源与状态

- 对应执行计划：[implementation-plan.md](implementation-plan.md)，计划第 2 版（`Plan conclusion: APPROVED`）。
- 需求来源：负责人 2026-10-20 的指示（Stage 2 划分；“contact_state.py 收敛为 CLI 分发与确有调用方依赖的兼容入口”）；范围与约束见执行计划。
- Target repository revision: 工作分支 `refactor-stage2-resolve-commit`，基线为 `origin/refactor-stage2-resolve` 的 `3233810`（其中实现提交为 `f07abb0`）；对照基准同为 `f07abb0` 的 `scripts` 目录。第 2 批分支在实施期间变基到已合并的 `main`，原任务给出的 `2ecdc9c` 已被替换；本计划按变基后的最新基线与同一批代码内容执行。
- Test plan revision: 第 5 版。
- 测试范围依据：`Test Engineer Rule.md`。本清单是验收上限，只覆盖本批明确要达到的目标与本次直接改变的行为。
- Proposed review status: 待复核（第 2–5 版意见已按 B1–B4、R1r/R5b/R6 与版本号、批次归属、退出码三项处理）。

## 必测清单

| 编号 | 业务目标 | 输入 / 场景 | 预期结果 | 检查方式 |
| --- | --- | --- | --- | --- |
| T0 | 模块可编译、可加载，工厂契约完整（R1、R3） | 工作树 `scripts/contact_state.py`、`scripts/_stage2_resolve.py` | 两个文件 `py_compile` 成功；直接执行 runner 的 `--help` 退出码 0；模块 `build()` 的 keyword-only 参数**精确等于** 14 个名字集合（不含 `_facts_preflight_proof`、`_load_existing_resolved`，含 5 个新增名字）；返回 23 个成员；runner 的 23 个别名逐个满足 `目标名 == _stage2_resolve.<同名>` 且去重后仍是 23 个；模块头有 `import json` | 第 1 步命令；4 条 `T0 ... OK`（14 参数、23 成员、23 同名别名、import json）与 `T0 CHECKS PASS` |
| T1 | 7 个函数确实离开 runner 顶层、进入模块 `build()`（R1） | 对照基准（`git archive f07abb0` 取出的 `scripts`）与工作树 `scripts` | `T0`：base 与 head 是两个不同目录、base 仍定义 7 个函数、head 一个都不定义；`T1`：模块存在；7 个函数逐个“runner 顶层已无 / 模块 `build()` 内有” | 第 2 步对比脚本的 `T0 ...` 与 `T1 ...` 行；共 18 条 `OK` |
| T2 | 搬移没有改变任何函数逻辑（R2） | 同上两侧源码 | 7 个函数的代码 AST 与基准完全相同（对比脚本忽略 docstring 内容）；docstring 单独核对：7 个函数都有 docstring（其中 6 个多行），`inspect.cleandoc` 后与基准同文；runner 其余顶层定义 AST 不变；离开 runner 的定义正好是这 7 个、没有新增；7 个函数在 runner 都有别名 | 同一对比脚本的 `T2 ...` 行；共 10 条 `OK`；docstring 核对用 `/tmp/pc-stage2-tools/check_docstrings.py`（sha256 `941b2220…`），末行 `total=7 with_doc=7 multi=6 clean_equal=7 without_doc=0 missing=0 mismatched=0` 与 `DOCSTRING CHECKS PASS` |
| T3 | 旧接口与加载方式不变（R4、R5） | 同一进程内分别按文件路径加载两侧 runner；再以子进程直接执行改动后的 runner | 7 个名字在两侧都可调用；`inspect.signature` 字符串两侧相同；直接执行 `contact_state.py --help` 退出码 0 | 同一对比脚本的 `T3 ...` 行；共 15 条 `OK`，末尾 `ALL CHECKS PASS` |
| T4 | resolve 提交层的校验、写入与用户选择边界不变（R2） | 既有测试方法 7 个（见第 3 步）：`ResolvedDirectionFinalizeTests` 3 个、`ResolvedDirectionRegressionTests` 2 个（运行隔离、旧 result 文件被忽略的直接调用）、`ResolveAcceptanceBoundaryTests` 1 个、`UserKeptProvisionalTests` 1 个 | 7 个方法执行；**通过条件只限落在本批 7 个函数上的断言**（结果文件必需性与本轮身份、移除校验、运行隔离、旧 result 文件被忽略、accept 的 key/陈旧校验、keep-provisional 写入）。方法内另有跨批断言：方法 1–4 的 plan 断言来自第 2 批 `cmd_stage2_resolve_plan`，方法 7 尾段经 `stage2-finalize` 断言 pack 的 `resolved_direction`（该命令尚未搬移）。这些断言失败时先按本批回归排查，按第 8 条命令在 `f07abb0` 上跑同一组方法，基线上也失败才记既有失败。`Stage2FinalizeWithResolvedTests` 的 3 个方法主断言在第 4 批，已从本批 T4 移出 | 第 3 步命令；`Ran 7 tests`、`OK`，无 skip／`FAIL`／`ERROR`；有失败时按第 8 条基线对照归因 |
| T5 | 复制 runner 的既有夹具仍能加载新模块（R4） | `test_stage5_immutable.TestWrapperKeepsInstalledLayoutLocator.test_finalize_through_wrapper_certifies_installed_layout_checker`、`test_stage5_dualtarget_contract.InstalledSharedSkillsLocatorTests.test_installed_shared_skills_layout_locator_finds_sibling` | 两个方法通过；复制布局包含 `_stage2_resolve.py`，复制后的 runner 能按路径加载它 | 第 4 步命令；`Ran 2 tests`、`OK`，无 skip |

**既有仓库检查（不属于本批业务必测清单）**：仓库 CI 的 `shards` 4 个分片与聚合 job `test` 由仓库工作流照常执行，其结果单独引用；本批不因此扩张或缩减必测清单，也不在本地重跑全量套件。

## 执行步骤

准备与执行都在工作树 `/Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage2-resolve-commit` 内进行；临时脚本与运行产物放仓库外 `/tmp` 目录。

1. T0：编译、直接执行与工厂契约检查（同一命令块，`set -e`）：

   ```sh
   set -e
   cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage2-resolve-commit
   uv run --no-project python --version
   uv run --no-project python -m py_compile \
     .apm/skills/professor-contact/scripts/contact_state.py \
     .apm/skills/professor-contact/scripts/_stage2_resolve.py
   uv run --no-project python .apm/skills/professor-contact/scripts/contact_state.py --help >/dev/null
   uv run --no-project python - <<'PY'
   import ast
   from pathlib import Path

   runner = ast.parse(Path('.apm/skills/professor-contact/scripts/contact_state.py').read_text())
   module = ast.parse(Path('.apm/skills/professor-contact/scripts/_stage2_resolve.py').read_text())
   build = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == 'build')
   args = {a.arg for a in build.args.kwonlyargs}
   expected = {'AUTHORSHIP_RANK', 'Stage2Context', 'direction_candidate_keys',
              'selected_candidate_union', 'emit', 'fail', 'filename_component',
              'sha256_obj', 'truncate', 'atomic_json', 'RESOLVED_DIRECTION_SCHEMA',
              'now_utc', 'read_json_file', 'direction_provisional_member_keys'}
   assert args == expected, (sorted(args), sorted(expected - args), sorted(args - expected))
   print('T0 build has exactly the 14 keyword-only parameters OK')
   returned = next(n for n in ast.walk(build)
                   if isinstance(n, ast.Return) and isinstance(n.value, ast.Call)
                   and ast.unparse(n.value.func) == 'types.SimpleNamespace')
   assert len(returned.value.keywords) == 23
   print('T0 build returns 23 members OK')
   aliases = [n for n in runner.body if isinstance(n, ast.Assign)
              and isinstance(n.targets[0], ast.Name)
              and ast.unparse(n.value).startswith('_stage2_resolve.')]
   assert len(aliases) == 23
   assert len({n.targets[0].id for n in aliases}) == 23
   assert all(ast.unparse(n.value) == '_stage2_resolve.' + n.targets[0].id for n in aliases)
   print('T0 runner has 23 same-name module aliases OK')
   assert any(isinstance(n, ast.Import) and any(a.name == 'json' for a in n.names)
              for n in module.body)
   print('T0 module imports json OK')
   print('T0 CHECKS PASS')
   PY
   ```

   预期：`py_compile` 与 `--help` 无输出且退出码 0；检查脚本打印 4 条 `T0 ... OK`（14 参数、23 成员、23 同名别名、import json）与 `T0 CHECKS PASS`。

2. T1–T3：取出对照基准并运行对比脚本（**同一个命令块，`RUN` 在同一 shell 进程内**）：

   ```sh
   set -e
   cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage2-resolve-commit
   RUN=/tmp/pc-stage3
   rm -rf "$RUN/base"
   mkdir -p "$RUN/base"
   git archive f07abb0 .apm/skills/professor-contact/scripts | tar -x -C "$RUN/base"
   shasum -a 256 /tmp/pc-stage2-tools/compare_stage2_batch.py
   uv run --no-project /tmp/pc-stage2-tools/compare_stage2_batch.py \
     "$RUN/base/.apm/skills/professor-contact/scripts" \
     .apm/skills/professor-contact/scripts \
     _stage2_resolve _stage2_resolve \
     validate_resolve_results _load_existing_resolved _facts_preflight_proof \
     _sidecar_preflight_proof _check_resolved_proof_binding \
     cmd_stage2_resolve_finalize cmd_stage2_resolve_accept
   shasum -a 256 /tmp/pc-stage2-tools/check_docstrings.py
   uv run --no-project /tmp/pc-stage2-tools/check_docstrings.py \
     "$RUN/base/.apm/skills/professor-contact/scripts" \
     .apm/skills/professor-contact/scripts \
     contact_state.py _stage2_resolve.py \
     validate_resolve_results _load_existing_resolved _facts_preflight_proof \
     _sidecar_preflight_proof _check_resolved_proof_binding \
     cmd_stage2_resolve_finalize cmd_stage2_resolve_accept
   ```

   对比脚本来源为既有的 `/tmp/pc-stage2-tools/compare_stage2_batch.py`（91 行），本批只调用、不改写；参考 sha256 为 `75c151c3ad3f9fd71c031d72b85a820a2b29b45229658f50212534c0798adff7`。脚本缺失或哈希不同时停止并交计划所有人，不凭提纲重写脚本。
   预期：43 条 `OK`（`T0` 3 条、`T1` 15 条、`T2` 10 条、`T3` 15 条），末尾 `ALL CHECKS PASS`，退出码 0。

   docstring 单独核对由 `/tmp/pc-stage2-tools/check_docstrings.py`（107 行，sha256 `941b2220a583bd849330f863a8ccc9de744d9d158fefb849d228e99be66e9bc3`）执行；本批新增该一次性脚本，只读两侧源码，不参与 T1–T3 判据。脚本缺失或哈希不同时停止并交计划所有人。
   预期：`total=7 with_doc=7 multi=6 clean_equal=7 without_doc=0 missing=0 mismatched=0`、`DOCSTRING CHECKS PASS`，退出码 0。

3. T4：只跑清单列出的 7 个方法。

   ```sh
   set -e
   cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage2-resolve-commit/.apm/skills/professor-contact/tests
   uv run --no-project python -m unittest \
     test_stage2_resolved_direction.ResolvedDirectionFinalizeTests.test_resolve_finalize_rejects_missing_new_result \
     test_stage2_resolved_direction.ResolvedDirectionFinalizeTests.test_resolve_finalize_applies_removal \
     test_stage2_resolved_direction.ResolvedDirectionFinalizeTests.test_resolve_finalize_rejects_invalid_removal \
     test_stage2_resolved_direction_regressions.ResolvedDirectionRegressionTests.test_resolve_run_isolation_and_missing_results \
     test_stage2_resolved_direction_regressions.ResolvedDirectionRegressionTests.test_reused_direction_ignores_stale_result_file \
     test_stage2_resolved_direction.ResolveAcceptanceBoundaryTests.test_resolve_accept_command_validates_keys_and_staleness \
     test_stage2_resolved_direction.UserKeptProvisionalTests.test_user_kept_provisional_still_writes_explicit_resolved_direction \
     -v
   ```

   预期：`Ran 7 tests`，全部 `ok`；无 `skipped`、`FAIL`、`ERROR`；若失败，按第 8 条的基线对照命令归因（先怀疑本批回归，基线上同样失败才算既有失败）。

4. T5：只跑清单列出的 2 个夹具方法。

   ```sh
   set -e
   cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage2-resolve-commit/.apm/skills/professor-contact/tests
   uv run --no-project python -m unittest \
     test_stage5_immutable.TestWrapperKeepsInstalledLayoutLocator.test_finalize_through_wrapper_certifies_installed_layout_checker \
     test_stage5_dualtarget_contract.InstalledSharedSkillsLocatorTests.test_installed_shared_skills_layout_locator_finds_sibling \
     -v
   ```

   预期：`Ran 2 tests`，全部 `ok`；无 `skipped`、`FAIL`、`ERROR`。

5. 既有仓库检查（不属于本批必测项，也不作为通过条件）：本批不在本地把全量套件列为必测步骤；PR #112 的 CI 在 head `1b08b36`（run `39315290639`）、`21e1af0`（run `39319465479`）、`88eba77`（run `39323008051`）、`e56bfd8`（run `39323797206`）上均为 4 个 `shards (shardN)` 与聚合 job `test` 全部 SUCCESS；后三个提交只改 `plan/` 文档，之后纯文档提交的 CI 结果只在 PR 页面查看，不再逐条写入本计划。

6. 失败注入：本批不适用。本批只把 7 个函数原样搬入模块并调整 `build()` 依赖，不修改写入顺序、错误通道或回滚逻辑；业务必测清单里也没有失败注入项。

7. 记录：把命令、实际提交 SHA、逐项结果与必要输出片段写入 `/tmp` 运行目录，并把方法与结果写入 `test-execution-<日期>.md`；CI 结果按运行编号与所跑 head 单独记录。

8. 失败处理：
   - T0 失败：按报错定位到编译、加载或 `build()` 契约；属于本批改动缺陷时交实现负责人修正后重跑第 1 步。
   - T1–T3 任一 `FAIL`：按标签定位到具体函数或检查项，判定为搬移缺陷，交实现负责人修正后重跑第 2 步；不得改脚本放宽判据。
   - T4／T5 方法失败：区分“本次改动引入的回归”“既有失败”“环境问题”。断言落在跨批代码（本批方法 1–4 经 `stage2-resolve-plan` 得出的 plan 断言属第 2 批；方法 7 尾段经 `stage2-finalize` 对 pack 的断言属尚未搬移的部分）时，也先按本批回归排查，用下面的命令在基线 `f07abb0` 上跑同一组方法：

     ```sh
     set -e
     BASELINE=/tmp/pc-stage3/base-f07abb0
     rm -rf "$BASELINE"
     mkdir -p "$BASELINE"
     git -C /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage2-resolve-commit archive f07abb0 | tar -x -C "$BASELINE"
     cd "$BASELINE/.apm/skills/professor-contact/tests"
     if uv run --no-project python -m unittest \
       test_stage2_resolved_direction.ResolvedDirectionFinalizeTests.test_resolve_finalize_rejects_missing_new_result \
       test_stage2_resolved_direction.ResolvedDirectionFinalizeTests.test_resolve_finalize_applies_removal \
       test_stage2_resolved_direction.ResolvedDirectionFinalizeTests.test_resolve_finalize_rejects_invalid_removal \
       test_stage2_resolved_direction_regressions.ResolvedDirectionRegressionTests.test_resolve_run_isolation_and_missing_results \
       test_stage2_resolved_direction_regressions.ResolvedDirectionRegressionTests.test_reused_direction_ignores_stale_result_file \
       test_stage2_resolved_direction.ResolveAcceptanceBoundaryTests.test_resolve_accept_command_validates_keys_and_staleness \
       test_stage2_resolved_direction.UserKeptProvisionalTests.test_user_kept_provisional_still_writes_explicit_resolved_direction \
       -v > /tmp/pc-stage3/t4-baseline.log 2>&1; then
       cat /tmp/pc-stage3/t4-baseline.log
       echo "BASELINE PASSED: 基线同样通过，工作树失败即本批回归"
     else
       cat /tmp/pc-stage3/t4-baseline.log
       echo "BASELINE FAILED: 基线同样失败，记既有失败"
       exit 1
     fi
     ```

     判据由块自身的退出码与末行给出：末行 `BASELINE PASSED` 且退出码 0＝基线通过，此时工作树失败就是本批引入的回归，修正后重跑第 3 步；末行 `BASELINE FAILED` 且退出码 1＝基线同样失败，记既有失败并保留 `t4-baseline.log`。块内的测试输出用重定向而不是 `| tee`，避免 `tee` 的退出码把测试失败吞掉。当前 7 个方法在基线与工作树上都通过，未触发该路径。
   - 既有跳过项按未执行记录，不算失败；不做无新信息的重复运行。
   - 仓库 CI 失败时按合并规则处理，不并入本批必测结论。

## 环境与预检

- 使用仓库现有的 `uv run --no-project python`（执行记录写明实际版本）与既有测试夹具，不新增依赖、不新增判定器或采集器；对比脚本只用标准库。
- 测试只使用合成数据与临时目录；不接触用户业务资料。
- 预检只确认命令可用、工作树状态、对照基准能取出；不预先执行业务目标命令求结果。
- 对照的两侧都从同一 `f07abb0` 与工作树 HEAD 的 `scripts` 目录取出，避免用不同版本的兄弟模块比较。
- 第 2 步的 `shasum -a 256` 是 macOS 写法；若在 Linux 复跑，改用 `sha256sum`，判据不变：`compare_stage2_batch.py` 91 行、哈希 `75c151c3ad3f9fd71c031d72b85a820a2b29b45229658f50212534c0798adff7`；`check_docstrings.py` 107 行、哈希 `941b2220a583bd849330f863a8ccc9de744d9d158fefb849d228e99be66e9bc3`。

## 不纳入本清单的范围

| 未纳入项 | 原因 |
| --- | --- |
| 新模块单独的可导入性单测 | 属内部组织；T0 的直接执行、T3 的按路径加载与 T5 的两条复制加载路径已覆盖真实加载方式 |
| 第 2 批已搬的 16 个函数与 7 个常量 | 本批不动；T2 的“其余顶层定义不变”与既有测试已覆盖 runner 侧，模块侧由实现检查保证 |
| `Stage2Context`、`stage2-finalize` 层、校验与 refine | 本批不动，属第 4–6 批 |
| 各函数内部逻辑的逐分支重测 | 本批是原样搬移；T2 的 AST 等价与既有测试已覆盖 |
| 全仓逐模块回归以外的性能／并发检查 | 本次改动不触及并发、事务或性能路径 |

## 自检

提交审核前逐条核对：① 必测项只引用能证明本批目标的方法，T4 只限本批 7 个函数的断言（跨批断言按第 8 条的基线对照归因）、T5 只限复制/加载；② CI 不在必测清单；③ 两个脚本都有确切来源、调用命令与 sha256；④ 命令块启用 `set -e` 且 `RUN` 在同一 shell 进程内使用；⑤ 失败注入标为“本批不适用”并说明原因；⑥ 计划文字与执行记录使用同一套编号；⑦ 编号与版本一致；⑧ 失败处理里的基线对照块能直接执行，且失败与通过由退出码区分（不把测试输出管道给 `tee`）。

## 修订记录

- 第 1 版：首次提交。按本批范围设 T0（编译／加载／工厂契约）、T1–T3（既有对比脚本的结构、AST、接口检查）、T4（9 个既有测试方法）、T5（2 个复制夹具方法）。实施期间第 2 批分支变基，对照基准由 `2ecdc9c` 更新为 `f07abb0`（同一批代码内容），判据与步骤不变。
- 第 2 版：按第一/二关审核修正——① T4 移出 3 个主断言在第 4 批的 `Stage2FinalizeWithResolvedTests` 方法，加入直接调用 `validate_resolve_results` 的 `test_reused_direction_ignores_stale_result_file`，T4 变 7 个并写明断言级归因；② T0 的内联脚本改为精确 14 参数集合、23 个同名别名（`目标名 == _stage2_resolve.<同名>`）、import json；③ T2 改为“脚本忽略 docstring + 单独核对 7/7 同文（6 个多行）”；④ 执行记录补 CI run `39315290639`（head `1b08b36`）与 7 个方法结果。

- 第 3 版：按第二关复核修正（R1–R5）——① T0 增补“23 个别名去重后仍 23”（`assert len({n.targets[0].id for n in aliases}) == 23`）；② 第 2 步补 docstring 核对命令与脚本 sha256，T2 与环境节写明脚本路径、行数与哈希；③ T4 归因改为基线对照——跨批断言失败先在 `f07abb0` 上跑同一方法，基线上也失败才算既有失败，否则按本批回归修正；④ 自检项 ③ 改为“两个脚本都有来源与 sha256”。
- 第 5 版：按第二关复核的剩余三点修正——① 计划头 `Test plan revision` 与 `Proposed review status` 同步到第 4/5 版；② 基线对照块改为 `if … then … else … exit 1`，用退出码区分 `BASELINE PASSED` 与 `BASELINE FAILED`，不再用 `| tee`；③ CI 记录补 `e56bfd8`／`39323797206`，并写明纯文档提交的结果只在 PR 页面查看。
- 第 4 版：按第二关复核的剩余点修正（R1r、R5b、R6）——① 跨批断言改按实测写明：方法 1–4 的 plan 断言来自第 2 批 `cmd_stage2_resolve_plan`，方法 7 尾段经 `stage2-finalize` 断言 pack 的 `resolved_direction`，不再笼统写“第 1/2 批 plan、第 4 批 finalize”；② 第 8 条补可执行的基线对照命令块（`/tmp/pc-stage3/base-f07abb0`、7 个方法、`tee /tmp/pc-stage3/t4-baseline.log`）与两条判据；③ 第 5 条的 CI 记录统一到实际 head：`1b08b36`／`39315290639`、`21e1af0`／`39319465479`、`88eba77`／`39323008051`。

## 审核状态

- 第 1 版：第一关/第二关 NEEDS_MODIFICATION（B1 T4 含第 4 批方法；B2 别名/kwargs 未验证；B3 docstring 判据；B4 CI 记录）。
- 第 2 版：第一关 PASS；第二关 NEEDS_MODIFICATION（R1–R6）。
- 第 3 版：第一关 PASS；第二关 NEEDS_MODIFICATION（R1r 执行记录残留、R5b 基线对照无命令、R6 CI 记录待统一）。
- 第 4 版：第一关 PASS；第二关 NEEDS_MODIFICATION（版本号不一致、批次归属写错、基线块退出码被 `tee` 吞掉）。
- 第 5 版：第一关 PASS；第二关待复核。
