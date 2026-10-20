# Stage 4 划分：最终写入与迁移（测试计划）

## 版本、来源与状态

- 对应执行计划：[implementation-plan.md](implementation-plan.md)，计划第 1 版（待审核）。
- Target repository revision: 工作分支 `refactor-stage4`；对照基准为父分支 `refactor-stage5-commands`（#121）的 head，命令里用 `git rev-parse` 动态取（当前 `8c4b363`）。
- Test plan revision: 第 2 版。
- 测试范围依据：`Test Engineer Rule.md`。

## 必测清单

| 编号 | 业务目标 | 输入 / 场景 | 预期结果 | 检查方式 |
| --- | --- | --- | --- | --- |
| T0 | 模块可编译、可加载，工厂契约与别名顺序正确（R1、R3、R4） | 工作树 `scripts/contact_state.py`、`scripts/_stage4_commands.py` | `py_compile` 成功；`--help` 退出码 0；`build()` 参数精确等于 27 个名字、无位置参数无默认值；返回 10 个成员；10 个同名别名；绑定调用晚于常量 `STAGE4_MIGRATION_COMMITTED`、10 个别名都晚于调用；模块不导入 runner（含 from-import 名）、无动态加载、不碰 `sys.path`／`sys.modules`；10 个名字不再在 runner 顶层定义 | 第 1 步命令；5 条 `T0 ... OK` + 1 条 `T0 CHECKS PASS` |
| T1 | 10 个定义确实离开 runner 顶层（R1） | 对照基准与工作树 | base 仍定义 10 个、head 一个都不定义；模块存在；逐个“runner 已无 / 模块 `build()` 内有” | 第 2 步脚本的 `T0`／`T1` 行，共 24 条 `OK` |
| T2 | 搬移没有改变逻辑（R2） | 两侧源码 | 10 个定义的 AST 完全相同；docstring 9 个有（6 个多行）清洗后同文、1 个原本没有；runner 其余函数/类定义不变；离开的是这 10 个；10 个都有别名 | 同一脚本的 `T2` 行（13 条 `OK`）+ docstring 段 |
| T3 | 旧接口与加载方式不变（R3、R4、R5） | 两侧 runner | 10 个名字都可调用、签名相同；`--help` 逐字节相同；用 `Path(__file__).with_name("_stage4_commands.py")` 加载；27 个实参同名同集合、10 个别名在调用之后 | 同一脚本的 `T3` 行（21 条 `OK`）+ 第 1 步的源码约束核对；合计 **58 条 `OK`**、`ALL CHECKS PASS` |
| T4 | `stage4-finalize` 与 `stage4-migrate-local` 的行为不变（R2） | 10 个既有方法（7 个只经 `stage4-finalize`、2 个只经 `stage4-migrate-local`、1 个同时覆盖两者；均走真实 CLI 子进程）：`test_contact_state.TestRunnerBasics` 的 6 个（`test_06_email_pack_exact_join_only`、`test_06b_papers_override_controls_email_order`、`test_06c_invalid_papers_override_does_not_write`、`test_06d_duplicate_stage4_selection_is_rejected_before_write`、`test_06f_stage4_preserves_previous_direction_selection`、`test_10_email_pack_self_contained`）；`test_contact_state.TestRunnerBasics.test_04_profile_change_invalidates_stage3_not_stage2`；`test_contact_state.Issue67ProfessorLocalStage4Tests` 的 3 个（`test_10_complete_local_pair_outranks_conflicting_legacy_rows`、`test_08_scoped_migration_recompiles_current_facts_and_skips_foreign_legacy`、`test_11_legacy_row_that_matches_surface_but_not_current_facts_writes_no_pair`） | **条件式通过条件**：10 个方法全部 `ok` 则通过；有失败时按第 5 步只对照**同一个失败方法**。注意 `test_04` 与 `test_06f` 同时驱动 stage3 命令；3 个 `Issue67ProfessorLocalStage4Tests` 方法合计覆盖两条命令，其中只有 `test_10` 同时驱动 finalize 与 migrate。失败时先单方法对照，不直接算本批回归 | 第 3 步命令；`Ran 10 tests`、`OK`。输出落 `/tmp/pc-stage14/t4.log` |
| T5 | 复制 runner 的既有夹具仍能加载新模块（R1、R5） | `test_stage5_immutable.TestWrapperKeepsInstalledLayoutLocator.test_finalize_through_wrapper_certifies_installed_layout_checker`、`test_stage5_dualtarget_contract.InstalledSharedSkillsLocatorTests.test_installed_shared_skills_layout_locator_finds_sibling` | 两方法 `OK` 只证明复制布局含 `_stage4_commands.py` 并成功加载；业务断言属 Stage 5，失败时单方法对照 | 第 4 步命令；`Ran 2 tests`、`OK`。输出落 `/tmp/pc-stage14/t5.log` |

**既有仓库检查（不属于本批业务必测清单）**：仓库 CI 的 4 个 `shards` 与聚合 job `test` 照常执行，不作为通过条件。

## 执行步骤

1. T0（编译、工厂契约、别名顺序、模块源码约束）：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage4
RUN=/tmp/pc-stage14
mkdir -p "$RUN"
uv run --no-project python --version
uv run --no-project python -m py_compile \
  .apm/skills/professor-contact/scripts/contact_state.py \
  .apm/skills/professor-contact/scripts/_stage4_commands.py
uv run --no-project python .apm/skills/professor-contact/scripts/contact_state.py --help >"$RUN/help-head.txt"
uv run --no-project python - <<'PY'
import ast
from pathlib import Path

SCRIPTS = Path(".apm/skills/professor-contact/scripts")
NAMES = ["_stage4_cross_group", "validate_stage4_selections", "stage4_local_pair_paths",
         "stage4_professor_row", "_stage4_failure_row", "_stage4_professor_commit",
         "stage4_professor_transaction", "cmd_stage4_finalize", "_stage4_migration_result",
         "cmd_stage4_migrate_local"]
EXPECTED_PARAMS = set("""atomic_json_many emit ProfessorBusinessFailure professor_business_channel
fail soft_exit contact_evidence_snapshot load_contact_evidence MANAGED_BY STAGE4_LOCAL_SCHEMA
DIRECTION_IDENTITY_VERSION SELECTION_KIND EMAIL_PACK_KIND EMAIL_PACK SELECTION_FILE now_utc
read_json_file professor_dir_containment_error direction_machine_id load_input_pack
load_candidate_state profile_fingerprint compile_email_entry validate_papers_override
_selection_direction_ids canonical_professor_dir STAGE4_MIGRATION_COMMITTED""".split())

runner_src = (SCRIPTS / "contact_state.py").read_text()
runner = ast.parse(runner_src)
module = ast.parse((SCRIPTS / "_stage4_commands.py").read_text())

build = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == "build")
args = {a.arg for a in build.args.kwonlyargs}
assert args == EXPECTED_PARAMS, (len(args), sorted(EXPECTED_PARAMS - args), sorted(args - EXPECTED_PARAMS))
assert not build.args.args and not build.args.posonlyargs and not build.args.vararg and not build.args.kwarg
assert all(d is None for d in build.args.kw_defaults), build.args.kw_defaults
returned = next(n for n in ast.walk(build) if isinstance(n, ast.Return)
                and isinstance(n.value, ast.Call) and ast.unparse(n.value.func).endswith("SimpleNamespace"))
members = [k.arg for k in returned.value.keywords]
assert len(members) == 10 and set(members) == set(NAMES), members
print("T0 build takes exactly the 27 keyword-only parameters and returns 10 members OK")

aliases = [n for n in runner.body if isinstance(n, ast.Assign)
           and isinstance(n.targets[0], ast.Name)
           and ast.unparse(n.value).startswith("_stage4_commands.")]
assert len(aliases) == 10 and {n.targets[0].id for n in aliases} == set(NAMES)
assert all(ast.unparse(n.value) == "_stage4_commands." + n.targets[0].id for n in aliases)
print("T0 runner has the 10 same-name _stage4_commands aliases OK")

call = next(n for n in runner.body if isinstance(n, ast.Assign)
            and ast.unparse(n.targets[0]) == "_stage4_commands" and isinstance(n.value, ast.Call))
assert sorted(k.arg for k in call.value.keywords) == sorted(EXPECTED_PARAMS)
assert all(ast.unparse(k.value) == k.arg for k in call.value.keywords)
migration_constant = next(n for n in runner.body if isinstance(n, ast.Assign)
                          and any(getattr(t, "id", "") == "STAGE4_MIGRATION_COMMITTED" for t in n.targets))
assert call.lineno > migration_constant.lineno, (migration_constant.lineno, call.lineno)
assert all(a.lineno > call.end_lineno for a in aliases)
print("T0 binding and all 10 aliases sit after the moved commands OK")

assert 'Path(__file__).with_name("_stage4_commands.py")' in runner_src
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
print("T0 none of the 10 names is defined at runner top level OK")
print("T0 CHECKS PASS")
PY
```
运行该块时重定向到 `bash blk0.sh > /tmp/pc-stage14/t0.log 2>&1`。
预期：脚本 5 条 `T0 ... OK` + 1 条 `T0 CHECKS PASS`（日志首行还会打印 Python 版本）。

2. T1–T3（对照基准、`--help`、A/B；随后 docstring）：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage4
RUN=/tmp/pc-stage14
rm -rf "$RUN/base"
mkdir -p "$RUN/base"
BASE_SHA=$(git rev-parse origin/refactor-stage5-commands)
git archive "$BASE_SHA" .apm/skills/professor-contact/scripts | tar -x -C "$RUN/base"
uv run --no-project python "$RUN/base/.apm/skills/professor-contact/scripts/contact_state.py" --help >"$RUN/help-base.txt"
diff -u "$RUN/help-base.txt" "$RUN/help-head.txt"
wc -l /tmp/pc-stage2-tools/compare_stage2_batch_v2.py
shasum -a 256 /tmp/pc-stage2-tools/compare_stage2_batch_v2.py
uv run --no-project /tmp/pc-stage2-tools/compare_stage2_batch_v2.py \
  "$RUN/base/.apm/skills/professor-contact/scripts" \
  .apm/skills/professor-contact/scripts \
  _stage4_commands _stage4_commands \
  _stage4_cross_group validate_stage4_selections stage4_local_pair_paths stage4_professor_row \
  _stage4_failure_row _stage4_professor_commit stage4_professor_transaction cmd_stage4_finalize \
  _stage4_migration_result cmd_stage4_migrate_local >"$RUN/compare.log" 2>&1
cat "$RUN/compare.log"
```
预期：`diff` 无输出；**58 条 `OK`**（T0 3、T1 21、T2 13、T3 21）、`ALL CHECKS PASS`。输出落 `$RUN/compare.log`。

   随后 docstring 核对（依赖上一段导出的 `$RUN/base`）：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage4
RUN=/tmp/pc-stage14
wc -l /tmp/pc-stage2-tools/check_docstrings_v3.py
shasum -a 256 /tmp/pc-stage2-tools/check_docstrings_v3.py
uv run --no-project /tmp/pc-stage2-tools/check_docstrings_v3.py \
  "$RUN/base/.apm/skills/professor-contact/scripts" \
  .apm/skills/professor-contact/scripts \
  contact_state.py _stage4_commands.py \
  _stage4_cross_group validate_stage4_selections stage4_local_pair_paths stage4_professor_row \
  _stage4_failure_row _stage4_professor_commit stage4_professor_transaction cmd_stage4_finalize \
  _stage4_migration_result cmd_stage4_migrate_local >"$RUN/docstring.log" 2>&1
cat "$RUN/docstring.log"
```
预期整行：`total=10 with_doc=9 multi=6 clean_equal=9 without_doc=1 missing=0 mismatched=0` 与 `DOCSTRING CHECKS PASS`。

3. T4：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage4/.apm/skills/professor-contact/tests
uv run --no-project python -m unittest \
  test_contact_state.TestRunnerBasics.test_06_email_pack_exact_join_only \
  test_contact_state.TestRunnerBasics.test_06b_papers_override_controls_email_order \
  test_contact_state.TestRunnerBasics.test_06c_invalid_papers_override_does_not_write \
  test_contact_state.TestRunnerBasics.test_06d_duplicate_stage4_selection_is_rejected_before_write \
  test_contact_state.TestRunnerBasics.test_06f_stage4_preserves_previous_direction_selection \
  test_contact_state.TestRunnerBasics.test_10_email_pack_self_contained \
  test_contact_state.TestRunnerBasics.test_04_profile_change_invalidates_stage3_not_stage2 \
  test_contact_state.Issue67ProfessorLocalStage4Tests.test_10_complete_local_pair_outranks_conflicting_legacy_rows \
  test_contact_state.Issue67ProfessorLocalStage4Tests.test_08_scoped_migration_recompiles_current_facts_and_skips_foreign_legacy \
  test_contact_state.Issue67ProfessorLocalStage4Tests.test_11_legacy_row_that_matches_surface_but_not_current_facts_writes_no_pair \
  -v > /tmp/pc-stage14/t4.log 2>&1
cat /tmp/pc-stage14/t4.log
```
预期：`Ran 10 tests`、全部 `ok`；失败时先另存日志再重跑。

4. T5：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage4/.apm/skills/professor-contact/tests
uv run --no-project python -m unittest \
  test_stage5_immutable.TestWrapperKeepsInstalledLayoutLocator.test_finalize_through_wrapper_certifies_installed_layout_checker \
  test_stage5_dualtarget_contract.InstalledSharedSkillsLocatorTests.test_installed_shared_skills_layout_locator_finds_sibling \
  -v > /tmp/pc-stage14/t5.log 2>&1
cat /tmp/pc-stage14/t5.log
```
预期：`Ran 2 tests`、全部 `ok`。

5. 失败处理：只在父提交上对照**同一个失败方法**，日志放 `$BASELINE` 之外的 `logs/` 目录、按方法短名 + 时间戳命名；`METHOD` 默认值只是示例，实际要替换成真正失败的方法。
```sh
set -e
METHOD="${METHOD:-test_contact_state.TestRunnerBasics.test_06_email_pack_exact_join_only}"
BASE_SHA=$(git -C /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage4 rev-parse origin/refactor-stage5-commands)
BASELINE=/tmp/pc-stage14/base-${BASE_SHA:0:12}
LOGDIR=/tmp/pc-stage14/logs/base-${BASE_SHA:0:12}
mkdir -p "$LOGDIR"
LOG="$LOGDIR/baseline-${METHOD##*.}-$(date +%Y%m%d-%H%M%S).log"
if [ ! -f "$BASELINE/.apm/skills/professor-contact/tests/${METHOD%%.*}.py" ]; then
  rm -rf "$BASELINE"
  mkdir -p "$BASELINE"
  git -C /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage4 archive "$BASE_SHA" | tar -x -C "$BASELINE"
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
| `canonical_professor_dir`／`compile_email_entry` 等 6 个 helper | 本批按引用注入 |
| Stage 5 的 17 个 helper、迁移命令的其余部分 | 后续批次 |
| 全量套件的本地重跑 | 仓库 CI 已分片执行 |
| R6 的空行接缝 | 属实现侧核对 |

## 修订记录

- 第 1 版：首次提交（含演练实测的 58 条 OK、10＋2 个方法与 docstring 期望值）。
- 第 2 版：按第一关意见修正 T4——换掉 3 个不跑 CLI 的方法（CLI surface 断言、两份文档契约），改为 3 个 `Issue67ProfessorLocalStage4Tests` 方法（`test_08` 覆盖 migrate 成功路径、`test_11` 覆盖错误路径、`test_10` 同时跑 finalize 与 migrate）；表格与第 3 步命令同步，覆盖分布改为“7 个 finalize、2 个 migrate、1 个两者都跑”。

## 审核状态

- 第 1 版：第一关 NEEDS_MODIFICATION（T4 有 3 个方法不跑 CLI、0 个覆盖 migrate）。
- 第 2 版：待第一关复核。
