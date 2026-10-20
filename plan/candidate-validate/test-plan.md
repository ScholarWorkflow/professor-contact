# 候选与跨方向校验划分：候选结果校验（测试计划）

## 版本、来源与状态

- 对应执行计划：[implementation-plan.md](implementation-plan.md)，计划第 2 版。
- Target repository revision: 工作分支 `refactor-shared-helpers`；对照基准为父分支 `refactor-stage5-helpers`（#124）的 head，命令里用 `git rev-parse` 动态取（当前 `8e47d10`）。
- Test plan revision: 第 2 版。
- 测试范围依据：`Test Engineer Rule.md`。

## 必测清单

| 编号 | 业务目标 | 输入 / 场景 | 预期结果 | 检查方式 |
| --- | --- | --- | --- | --- |
| T0 | 模块可编译、可加载，工厂契约与别名顺序正确（R1、R3、R4） | 工作树 `scripts/contact_state.py`、`scripts/_candidate_validate.py` | `py_compile` 成功；`--help` 退出码 0；`build()` 参数精确等于 7 个名字、无位置参数无默认值；返回 5 个成员；5 个同名别名；绑定调用晚于 `_direction_slices`、且 5 个别名都晚于该调用并早于 `_stage3_commands` 的 build；模块不导入 runner、无动态加载、不碰 `sys.path`／`sys.modules`；5 个名字不再在 runner 顶层定义 | 第 1 步命令；5 条 `T0 ... OK` + 1 条 `T0 CHECKS PASS` |
| T1 | 5 个定义确实离开 runner 顶层（R1） | 对照基准与工作树 | base 仍定义 5 个、head 一个都不定义；模块存在；逐个“runner 已无 / 模块 `build()` 内有” | 第 2 步脚本的 `T0`／`T1` 行，共 14 条 `OK` |
| T2 | 搬移没有改变逻辑（R2） | 两侧源码 | 5 个定义的 AST 相同（比较时忽略 docstring）；docstring 3 个有（全多行）清洗后同文、2 个原本没有；runner 其余函数/类定义不变；离开的是这 5 个；5 个都有别名 | 同一脚本的 `T2` 行（8 条 `OK`）+ docstring 段 |
| T3 | 旧接口与加载方式不变（R3、R4、R5） | 两侧 runner | 5 个名字都可调用、签名相同；`--help` 逐字节相同；7 个实参与 `Path(__file__).with_name` 加载由第 1 步 T0 脚本核对；合计 **33 条 `OK`** | 同一脚本的 `T3` 行（11 条 `OK`：10 条 callable／签名 + 1 条 `--help`）+ 第 2 步 `diff -u` |
| T4 | 候选与跨方向校验的行为不变（R2） | 10 个既有方法（均经真实 CLI 子进程）：`test_contact_state.TestRunnerBasics` 的 6 个（`test_03_done_by_self_rejected_as_candidate_anchor`、`test_05b_collection_key_limits_stage3`、`test_05c_scoped_stage3_refresh_preserves_other_state`、`test_05d_scoped_stage3_rejects_six_generated_candidates`、`test_05e_overview_manual_edit_does_not_block_local_finalize`、`test_08_manual_markdown_edit_needs_decision`）；`test_contact_state.Issue67AdjacentStateTests.test_08_cross_selection_scope_refreshes_every_participating_direction`；`test_stage3_validation_refine.Stage3ValidationIngestTests.test_cross_direction_issue_routes_to_the_exact_group_id`；`test_issue66_stage3_local_state.Issue66LocalStateTests` 的 2 个（`test_rebuild_overview_uses_professor_local_states_and_rebuilds_deleted_projection`、`test_rebuild_overview_only_migrates_a_unique_legacy_identity`） | **条件式通过条件**：10 个方法全部 `ok` 则通过；有失败时按第 5 步只对照**同一个失败方法**。实际调用链：候选校验只发生在 `cmd_stage3_finalize`（8 个方法走它，其中 2 个覆盖跨方向组），`render_candidates_overview` 只由 `cmd_stage3_rebuild_overview` 调用（2 个 rebuild 方法覆盖）；`stage3-plan` 与 `migrate-v3` 本身不调用本批函数，因此不再列为本批覆盖 | 第 3 步命令；`Ran 10 tests`、`OK`。输出落 `/tmp/pc-stage17/t4.log` |
| T5 | 复制 runner 的既有夹具仍能加载新模块（R1、R5） | `test_stage5_immutable.TestWrapperKeepsInstalledLayoutLocator.test_finalize_through_wrapper_certifies_installed_layout_checker`、`test_stage5_dualtarget_contract.InstalledSharedSkillsLocatorTests.test_installed_shared_skills_layout_locator_finds_sibling` | 两方法 `OK` 只证明复制布局含 `_candidate_validate.py` 并成功加载；方法内业务断言属 Stage 5，失败时按第 5 步单方法对照 | 第 4 步命令；`Ran 2 tests`、`OK`。输出落 `/tmp/pc-stage17/t5.log` |

**既有仓库检查（不属于本批业务必测清单）**：仓库 CI 的 4 个 `shards` 与聚合 job `test` 照常执行，不作为通过条件。

## 执行步骤

1. T0（编译、工厂契约、别名顺序、模块源码约束）：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-shared-helpers
RUN=/tmp/pc-stage17
mkdir -p "$RUN"
uv run --no-project python --version
uv run --no-project python -m py_compile \
  .apm/skills/professor-contact/scripts/contact_state.py \
  .apm/skills/professor-contact/scripts/_candidate_validate.py
uv run --no-project python .apm/skills/professor-contact/scripts/contact_state.py --help >"$RUN/help-head.txt"
uv run --no-project python - <<'PY'
import ast
from pathlib import Path

SCRIPTS = Path(".apm/skills/professor-contact/scripts")
NAMES = ["_validate_candidate_core", "validate_candidate_result", "validate_cross_result",
         "render_candidates_md", "render_candidates_overview"]
EXPECTED_PARAMS = set("_stage3_render fail CANDIDATES_MD ANCHORABLE now_utc direction_machine_id _direction_slices".split())

runner_src = (SCRIPTS / "contact_state.py").read_text()
runner = ast.parse(runner_src)
module = ast.parse((SCRIPTS / "_candidate_validate.py").read_text())

build = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == "build")
args = {a.arg for a in build.args.kwonlyargs}
assert args == EXPECTED_PARAMS, (sorted(args), sorted(EXPECTED_PARAMS - args), sorted(args - EXPECTED_PARAMS))
assert not build.args.args and not build.args.posonlyargs and not build.args.vararg and not build.args.kwarg
assert all(d is None for d in build.args.kw_defaults), build.args.kw_defaults
returned = next(n for n in ast.walk(build) if isinstance(n, ast.Return)
                and isinstance(n.value, ast.Call) and ast.unparse(n.value.func).endswith("SimpleNamespace"))
members = [k.arg for k in returned.value.keywords]
assert len(members) == 5 and set(members) == set(NAMES), members
print("T0 build takes exactly the 7 keyword-only parameters and returns 5 members OK")

aliases = [n for n in runner.body if isinstance(n, ast.Assign)
           and isinstance(n.targets[0], ast.Name)
           and ast.unparse(n.value).startswith("_candidate_validate.")]
assert len(aliases) == 5 and {n.targets[0].id for n in aliases} == set(NAMES)
assert all(ast.unparse(n.value) == "_candidate_validate." + n.targets[0].id for n in aliases)
print("T0 runner has the 5 same-name _candidate_validate aliases OK")

call = next(n for n in runner.body if isinstance(n, ast.Assign)
            and ast.unparse(n.targets[0]) == "_candidate_validate" and isinstance(n.value, ast.Call))
assert sorted(k.arg for k in call.value.keywords) == sorted(EXPECTED_PARAMS)
assert all(ast.unparse(k.value) == k.arg for k in call.value.keywords)
direction = next(n for n in runner.body if isinstance(n, ast.FunctionDef) and n.name == "_direction_slices")
stage3 = next(n for n in runner.body if isinstance(n, ast.Assign)
              and ast.unparse(n.targets[0]) == "_stage3_commands" and isinstance(n.value, ast.Call))
assert direction.end_lineno < call.lineno < stage3.lineno, (direction.end_lineno, call.lineno, stage3.lineno)
assert all(a.lineno > call.end_lineno for a in aliases)
assert all(a.lineno < stage3.lineno for a in aliases)
print("T0 binding and all 5 aliases sit between _direction_slices and the stage3 commands factory OK")

assert 'Path(__file__).with_name("_candidate_validate.py")' in runner_src
imported = {a.name for n in ast.walk(module) if isinstance(n, ast.Import) for a in n.names}
imported |= {n.module or "" for n in ast.walk(module) if isinstance(n, ast.ImportFrom)}
assert not any("contact_state" in name for name in imported), sorted(imported)
assert not any("contact_state" in (n.module or "") or any("contact_state" in a.name for a in n.names)
               for n in ast.walk(module) if isinstance(n, ast.ImportFrom))
dotted = {ast.unparse(n) for n in ast.walk(module) if isinstance(n, ast.Attribute)}
assert not (dotted & {"sys.path", "sys.modules"}), sorted(dotted & {"sys.path", "sys.modules"})
dynamic = {"spec_from_file_location", "module_from_spec", "exec_module", "import_module"}
assert not {d for d in dotted if d.split(".")[-1] in dynamic}, sorted(dotted)
from_names = {a.name for n in ast.walk(module) if isinstance(n, ast.ImportFrom) for a in n.names}
assert not (from_names & (dynamic | {"path", "modules"})), sorted(from_names & (dynamic | {"path", "modules"}))
names_used = {n.id for n in ast.walk(module) if isinstance(n, ast.Name)}
assert not (names_used & {"__import__", "exec", "eval"}), sorted(names_used & {"__import__", "exec", "eval"})
print("T0 runner loads it by path, and the module has no runner import and no dynamic-import names OK")

assert [n for n in runner.body if isinstance(n, ast.FunctionDef) and n.name in NAMES] == []
print("T0 none of the 5 names is defined at runner top level OK")
print("T0 CHECKS PASS")
PY
```
运行该块时重定向到 `bash blk0.sh > /tmp/pc-stage17/t0.log 2>&1`。
预期：脚本 5 条 `T0 ... OK` + 1 条 `T0 CHECKS PASS`。

2. T1–T3（对照基准、`--help`、A/B；随后 docstring）：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-shared-helpers
RUN=/tmp/pc-stage17
rm -rf "$RUN/base"
mkdir -p "$RUN/base"
BASE_SHA=$(git rev-parse origin/refactor-stage5-helpers)
git archive "$BASE_SHA" .apm/skills/professor-contact/scripts | tar -x -C "$RUN/base"
uv run --no-project python "$RUN/base/.apm/skills/professor-contact/scripts/contact_state.py" --help >"$RUN/help-base.txt"
diff -u "$RUN/help-base.txt" "$RUN/help-head.txt"
wc -l /tmp/pc-stage2-tools/compare_stage2_batch_v2.py
shasum -a 256 /tmp/pc-stage2-tools/compare_stage2_batch_v2.py
uv run --no-project /tmp/pc-stage2-tools/compare_stage2_batch_v2.py \
  "$RUN/base/.apm/skills/professor-contact/scripts" \
  .apm/skills/professor-contact/scripts \
  _candidate_validate _candidate_validate \
  _validate_candidate_core validate_candidate_result validate_cross_result \
  render_candidates_md render_candidates_overview >"$RUN/compare.log" 2>&1
cat "$RUN/compare.log"
```
预期：`diff` 无输出；**33 条 `OK`**（T0 3、T1 11、T2 8、T3 11）、`ALL CHECKS PASS`。

   随后 docstring 核对：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-shared-helpers
RUN=/tmp/pc-stage17
wc -l /tmp/pc-stage2-tools/check_docstrings_v3.py
shasum -a 256 /tmp/pc-stage2-tools/check_docstrings_v3.py
uv run --no-project /tmp/pc-stage2-tools/check_docstrings_v3.py \
  "$RUN/base/.apm/skills/professor-contact/scripts" \
  .apm/skills/professor-contact/scripts \
  contact_state.py _candidate_validate.py \
  _validate_candidate_core validate_candidate_result validate_cross_result \
  render_candidates_md render_candidates_overview >"$RUN/docstring.log" 2>&1
cat "$RUN/docstring.log"
```
预期整行：`total=5 with_doc=3 multi=3 clean_equal=3 without_doc=2 missing=0 mismatched=0` 与 `DOCSTRING CHECKS PASS`。

3. T4：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-shared-helpers/.apm/skills/professor-contact/tests
uv run --no-project python -m unittest \
  test_contact_state.TestRunnerBasics.test_03_done_by_self_rejected_as_candidate_anchor \
  test_contact_state.TestRunnerBasics.test_05b_collection_key_limits_stage3 \
  test_contact_state.TestRunnerBasics.test_05c_scoped_stage3_refresh_preserves_other_state \
  test_contact_state.TestRunnerBasics.test_05d_scoped_stage3_rejects_six_generated_candidates \
  test_contact_state.TestRunnerBasics.test_05e_overview_manual_edit_does_not_block_local_finalize \
  test_contact_state.TestRunnerBasics.test_08_manual_markdown_edit_needs_decision \
  test_contact_state.Issue67AdjacentStateTests.test_08_cross_selection_scope_refreshes_every_participating_direction \
  test_stage3_validation_refine.Stage3ValidationIngestTests.test_cross_direction_issue_routes_to_the_exact_group_id \
  test_issue66_stage3_local_state.Issue66LocalStateTests.test_rebuild_overview_uses_professor_local_states_and_rebuilds_deleted_projection \
  test_issue66_stage3_local_state.Issue66LocalStateTests.test_rebuild_overview_only_migrates_a_unique_legacy_identity \
  -v > /tmp/pc-stage17/t4.log 2>&1
cat /tmp/pc-stage17/t4.log
```
预期：`Ran 10 tests`、全部 `ok`；失败时保存日志后进入第 5 步单方法对照。

4. T5：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-shared-helpers/.apm/skills/professor-contact/tests
uv run --no-project python -m unittest \
  test_stage5_immutable.TestWrapperKeepsInstalledLayoutLocator.test_finalize_through_wrapper_certifies_installed_layout_checker \
  test_stage5_dualtarget_contract.InstalledSharedSkillsLocatorTests.test_installed_shared_skills_layout_locator_finds_sibling \
  -v > /tmp/pc-stage17/t5.log 2>&1
cat /tmp/pc-stage17/t5.log
```
预期：`Ran 2 tests`、全部 `ok`。

5. 失败处理：只在父提交上对照**同一个失败方法**，日志放 `$BASELINE` 之外的 `logs/` 目录；`METHOD` 默认值只是示例，实际要替换成真正失败的方法。
```sh
set -e
METHOD="${METHOD:-test_contact_state.TestRunnerBasics.test_08_manual_markdown_edit_needs_decision}"
BASE_SHA=$(git -C /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-shared-helpers rev-parse origin/refactor-stage5-helpers)
BASELINE=/tmp/pc-stage17/base-${BASE_SHA:0:12}
LOGDIR=/tmp/pc-stage17/logs/base-${BASE_SHA:0:12}
mkdir -p "$LOGDIR"
LOG="$LOGDIR/baseline-${METHOD##*.}-$(date +%Y%m%d-%H%M%S).log"
if [ ! -f "$BASELINE/.apm/skills/professor-contact/tests/${METHOD%%.*}.py" ]; then
  rm -rf "$BASELINE"
  mkdir -p "$BASELINE"
  git -C /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-shared-helpers archive "$BASE_SHA" | tar -x -C "$BASELINE"
fi
cd "$BASELINE/.apm/skills/professor-contact/tests"
uv run --no-project python -m unittest "$METHOD" -v >"$LOG" 2>&1 || true
cat "$LOG"
```
判据：父提交同一个方法也失败＝既有失败；父提交通过而工作树失败＝本批回归。

6. 失败注入：本批不适用。本批只把定义搬到同目录模块并保持函数体逐字不变，不改事务、回滚、写入顺序、错误通道或 CLI 参数。

7. 既有仓库检查：PR 推送后引用 CI 运行编号，不作为通过条件。

## 不纳入本清单的范围

| 未纳入项 | 原因 |
| --- | --- |
| email core 的 4 个定义、contact evidence、stage1、profile/direction、verify 链、legacy 迁移 helper | 后续批次 |
| 全量套件的本地重跑 | 仓库 CI 已分片执行 |
| R6 的空行接缝 | 属实现侧核对 |

## 修订记录

- 第 1 版：首次提交（含演练实测的 33 条 OK、10＋2 个方法与 docstring 期望值）。
- 第 2 版：按第一关意见修正 T4——换掉 5 个不执行本批代码的方法（list-inputs、migrate-v3、进程内 normalize、issue59 夹具），改为 8 个走 `cmd_stage3_finalize` 的方法（其中 2 个覆盖跨方向组）与 2 个 `stage3-rebuild-overview` 方法，让 `render_candidates_overview` 也有行为覆盖；覆盖声明按实际调用链改写，删掉 stage3-plan／migrate-v3 的候选校验说法。

## 审核状态

- 第 1 版：第一关 NEEDS_MODIFICATION（5 个方法未到达本批代码、overview 无覆盖）。
- 第 2 版：待第一关复核。
