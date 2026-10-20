# 迁移命令划分：migrate-v3 的计划与执行（测试计划）

## 版本、来源与状态

- 对应执行计划：[implementation-plan.md](implementation-plan.md)，计划第 1 版（待审核）。
- Target repository revision: 工作分支 `refactor-migrate`；对照基准为父分支 `refactor-stage4`（#122）的 head，命令里用 `git rev-parse` 动态取（当前 `2c81bae`）。
- Test plan revision: 第 2 版。
- 测试范围依据：`Test Engineer Rule.md`。

## 必测清单

| 编号 | 业务目标 | 输入 / 场景 | 预期结果 | 检查方式 |
| --- | --- | --- | --- | --- |
| T0 | 模块可编译、可加载，工厂契约与别名顺序正确（R1、R3、R4） | 工作树 `scripts/contact_state.py`、`scripts/_migrate_commands.py` | `py_compile` 成功；`--help` 退出码 0；`build()` 参数精确等于 16 个名字、无位置参数无默认值；返回 4 个成员；4 个同名别名；绑定调用晚于 `apply_ready_entry`（16 个注入名里最晚，按 `end_lineno`）、4 个别名都晚于该调用；模块不导入 runner、无动态加载、不碰 `sys.path`／`sys.modules`；4 个名字不再在 runner 顶层定义 | 第 1 步命令；5 条 `T0 ... OK` + 1 条 `T0 CHECKS PASS` |
| T1 | 4 个定义确实离开 runner 顶层（R1） | 对照基准与工作树 | base 仍定义 4 个、head 一个都不定义；模块存在；逐个“runner 已无 / 模块 `build()` 内有” | 第 2 步脚本的 `T0`／`T1` 行，共 12 条 `OK` |
| T2 | 搬移没有改变逻辑（R2） | 两侧源码 | 4 个定义的 AST 完全相同；docstring 4 个都没有（基线如此）；runner 其余函数/类定义不变；离开的是这 4 个；4 个都有别名 | 同一脚本的 `T2` 行（7 条 `OK`）+ docstring 段 |
| T3 | 旧接口与加载方式不变（R3、R4、R5） | 两侧 runner | 4 个名字都可调用、签名相同；`--help` 逐字节相同；用 `Path(__file__).with_name("_migrate_commands.py")` 加载；16 个实参同名同集合、4 个别名在调用之后 | 同一脚本的 `T3` 行（9 条 `OK`：8 条 callable／签名 + 1 条 `T3 runner executes directly (--help)`）+ 第 1 步的源码约束核对 + 第 2 步的 `diff -u`（`--help` 逐字节相同）；合计 **28 条 `OK`**、`ALL CHECKS PASS` |
| T4 | `migrate-v3` 的 `--plan` 与 `--apply` 行为不变（R2） | 6 个既有方法（全部在 `test_contact_state.TestMigrate`，均经真实 CLI 子进程调用 `migrate-v3`）：`test_migrate_plan_legacy_needs_stage2`、`test_migrate_gap_id_mismatch_is_blocked`、`test_migrate_missing_metadata_is_not_ready`、`test_migrate_scans_no_category_fallback`（这 4 个只走 `--plan`）；`test_migrate_ready_apply_without_model`、`test_migrate_existing_input_pack_is_skipped`（这两个 `--plan` 与 `--apply` 都走） | **条件式通过条件**：6 个方法全部 `ok` 则通过；有失败时按第 5 步只对照**同一个失败方法** | 第 3 步命令；`Ran 6 tests`、`OK`。输出落 `/tmp/pc-stage15/t4.log` |
| T5 | 复制 runner 的既有夹具仍能加载新模块（R1、R5） | `test_stage5_immutable.TestWrapperKeepsInstalledLayoutLocator.test_finalize_through_wrapper_certifies_installed_layout_checker`、`test_stage5_dualtarget_contract.InstalledSharedSkillsLocatorTests.test_installed_shared_skills_layout_locator_finds_sibling` | 两方法 `OK` 只证明复制布局含 `_migrate_commands.py` 并成功加载；业务断言属 Stage 5，失败时单方法对照 | 第 4 步命令；`Ran 2 tests`、`OK`。输出落 `/tmp/pc-stage15/t5.log` |

**既有仓库检查（不属于本批业务必测清单）**：仓库 CI 的 4 个 `shards` 与聚合 job `test` 照常执行，不作为通过条件。

## 执行步骤

1. T0（编译、工厂契约、别名顺序、模块源码约束）：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-migrate
RUN=/tmp/pc-stage15
mkdir -p "$RUN"
uv run --no-project python --version
uv run --no-project python -m py_compile \
  .apm/skills/professor-contact/scripts/contact_state.py \
  .apm/skills/professor-contact/scripts/_migrate_commands.py
uv run --no-project python .apm/skills/professor-contact/scripts/contact_state.py --help >"$RUN/help-head.txt"
uv run --no-project python - <<'PY'
import ast
from pathlib import Path

SCRIPTS = Path(".apm/skills/professor-contact/scripts")
NAMES = ["migration_source_fingerprint", "migrate_entry_for_professor",
         "cmd_migrate_plan", "cmd_migrate_apply"]
EXPECTED_PARAMS = set("""atomic_json emit fail SCHEMA MANAGED_BY INPUT_PACK CANDIDATES_MD GAP_STATUSES
now_utc sha256_bytes sha256_obj read_json_file load_sidecar read_legacy_index classify_direction
apply_ready_entry""".split())

runner_src = (SCRIPTS / "contact_state.py").read_text()
runner = ast.parse(runner_src)
module = ast.parse((SCRIPTS / "_migrate_commands.py").read_text())

build = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == "build")
args = {a.arg for a in build.args.kwonlyargs}
assert args == EXPECTED_PARAMS, (len(args), sorted(EXPECTED_PARAMS - args), sorted(args - EXPECTED_PARAMS))
assert not build.args.args and not build.args.posonlyargs and not build.args.vararg and not build.args.kwarg
assert all(d is None for d in build.args.kw_defaults), build.args.kw_defaults
returned = next(n for n in ast.walk(build) if isinstance(n, ast.Return)
                and isinstance(n.value, ast.Call) and ast.unparse(n.value.func).endswith("SimpleNamespace"))
members = [k.arg for k in returned.value.keywords]
assert len(members) == 4 and set(members) == set(NAMES), members
print("T0 build takes exactly the 16 keyword-only parameters and returns 4 members OK")

aliases = [n for n in runner.body if isinstance(n, ast.Assign)
           and isinstance(n.targets[0], ast.Name)
           and ast.unparse(n.value).startswith("_migrate_commands.")]
assert len(aliases) == 4 and {n.targets[0].id for n in aliases} == set(NAMES)
assert all(ast.unparse(n.value) == "_migrate_commands." + n.targets[0].id for n in aliases)
print("T0 runner has the 4 same-name _migrate_commands aliases OK")

call = next(n for n in runner.body if isinstance(n, ast.Assign)
            and ast.unparse(n.targets[0]) == "_migrate_commands" and isinstance(n.value, ast.Call))
assert sorted(k.arg for k in call.value.keywords) == sorted(EXPECTED_PARAMS)
assert all(ast.unparse(k.value) == k.arg for k in call.value.keywords)
anchor = next(n for n in runner.body if isinstance(n, ast.FunctionDef) and n.name == "apply_ready_entry")
assert call.lineno > anchor.end_lineno, (anchor.end_lineno, call.lineno)
assert all(a.lineno > call.end_lineno for a in aliases)
print("T0 binding and all 4 aliases sit after apply_ready_entry OK")

assert 'Path(__file__).with_name("_migrate_commands.py")' in runner_src
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
print("T0 none of the 4 names is defined at runner top level OK")
print("T0 CHECKS PASS")
PY
```
运行该块时重定向到 `bash blk0.sh > /tmp/pc-stage15/t0.log 2>&1`。
预期：脚本 5 条 `T0 ... OK` + 1 条 `T0 CHECKS PASS`（日志首行还会打印 Python 版本）。

2. T1–T3（对照基准、`--help`、A/B；随后 docstring）：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-migrate
RUN=/tmp/pc-stage15
rm -rf "$RUN/base"
mkdir -p "$RUN/base"
BASE_SHA=$(git rev-parse origin/refactor-stage4)
git archive "$BASE_SHA" .apm/skills/professor-contact/scripts | tar -x -C "$RUN/base"
uv run --no-project python "$RUN/base/.apm/skills/professor-contact/scripts/contact_state.py" --help >"$RUN/help-base.txt"
diff -u "$RUN/help-base.txt" "$RUN/help-head.txt"
wc -l /tmp/pc-stage2-tools/compare_stage2_batch_v2.py
shasum -a 256 /tmp/pc-stage2-tools/compare_stage2_batch_v2.py
uv run --no-project /tmp/pc-stage2-tools/compare_stage2_batch_v2.py \
  "$RUN/base/.apm/skills/professor-contact/scripts" \
  .apm/skills/professor-contact/scripts \
  _migrate_commands _migrate_commands \
  migration_source_fingerprint migrate_entry_for_professor cmd_migrate_plan cmd_migrate_apply >"$RUN/compare.log" 2>&1
cat "$RUN/compare.log"
```
预期：`diff` 无输出；**28 条 `OK`**（T0 3、T1 9、T2 7、T3 9）、`ALL CHECKS PASS`。输出落 `$RUN/compare.log`。

   随后 docstring 核对（依赖上一段导出的 `$RUN/base`）：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-migrate
RUN=/tmp/pc-stage15
wc -l /tmp/pc-stage2-tools/check_docstrings_v3.py
shasum -a 256 /tmp/pc-stage2-tools/check_docstrings_v3.py
uv run --no-project /tmp/pc-stage2-tools/check_docstrings_v3.py \
  "$RUN/base/.apm/skills/professor-contact/scripts" \
  .apm/skills/professor-contact/scripts \
  contact_state.py _migrate_commands.py \
  migration_source_fingerprint migrate_entry_for_professor cmd_migrate_plan cmd_migrate_apply >"$RUN/docstring.log" 2>&1
cat "$RUN/docstring.log"
```
预期整行：`total=4 with_doc=0 multi=0 clean_equal=0 without_doc=4 missing=0 mismatched=0` 与 `DOCSTRING CHECKS PASS`（基线里这 4 个定义本来就没有 docstring）。

3. T4：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-migrate/.apm/skills/professor-contact/tests
uv run --no-project python -m unittest \
  test_contact_state.TestMigrate.test_migrate_plan_legacy_needs_stage2 \
  test_contact_state.TestMigrate.test_migrate_ready_apply_without_model \
  test_contact_state.TestMigrate.test_migrate_gap_id_mismatch_is_blocked \
  test_contact_state.TestMigrate.test_migrate_missing_metadata_is_not_ready \
  test_contact_state.TestMigrate.test_migrate_scans_no_category_fallback \
  test_contact_state.TestMigrate.test_migrate_existing_input_pack_is_skipped \
  -v > /tmp/pc-stage15/t4.log 2>&1
cat /tmp/pc-stage15/t4.log
```
预期：`Ran 6 tests`、全部 `ok`；若失败，保存该日志后进入第 5 步做单方法对照，不重复跑正式集合。

4. T5：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-migrate/.apm/skills/professor-contact/tests
uv run --no-project python -m unittest \
  test_stage5_immutable.TestWrapperKeepsInstalledLayoutLocator.test_finalize_through_wrapper_certifies_installed_layout_checker \
  test_stage5_dualtarget_contract.InstalledSharedSkillsLocatorTests.test_installed_shared_skills_layout_locator_finds_sibling \
  -v > /tmp/pc-stage15/t5.log 2>&1
cat /tmp/pc-stage15/t5.log
```
预期：`Ran 2 tests`、全部 `ok`。

5. 失败处理：只在父提交上对照**同一个失败方法**，日志放 `$BASELINE` 之外的 `logs/` 目录、按方法短名 + 时间戳命名；`METHOD` 默认值只是示例，实际要替换成真正失败的方法。
```sh
set -e
METHOD="${METHOD:-test_contact_state.TestMigrate.test_migrate_plan_legacy_needs_stage2}"
BASE_SHA=$(git -C /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-migrate rev-parse origin/refactor-stage4)
BASELINE=/tmp/pc-stage15/base-${BASE_SHA:0:12}
LOGDIR=/tmp/pc-stage15/logs/base-${BASE_SHA:0:12}
mkdir -p "$LOGDIR"
LOG="$LOGDIR/baseline-${METHOD##*.}-$(date +%Y%m%d-%H%M%S).log"
if [ ! -f "$BASELINE/.apm/skills/professor-contact/tests/${METHOD%%.*}.py" ]; then
  rm -rf "$BASELINE"
  mkdir -p "$BASELINE"
  git -C /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-migrate archive "$BASE_SHA" | tar -x -C "$BASELINE"
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
| `read_legacy_index`／`classify_direction`／`apply_ready_entry` 等 helper | 本批按引用注入 |
| Stage 5 的 17 个组装/渲染 helper | 后续批次 |
| 全量套件的本地重跑 | 仓库 CI 已分片执行 |
| R6 的空行接缝 | 属实现侧核对 |

## 修订记录

- 第 1 版：首次提交（含演练实测的 28 条 OK、6＋2 个方法与 docstring 期望值）。
- 第 2 版：按第一关意见修正——T0 的 R4 分句改成“绑定调用晚于 `apply_ready_entry`、别名晚于调用”（与脚本一致）；T3 的检查方式补第 2 步 `diff`；第 3 步失败处理改为“保存日志后进入第 5 步单方法对照”。

## 审核状态

- 第 1 版：第一关 NEEDS_MODIFICATION（T0 的 R4 锚点写成已搬走的 `cmd_migrate_apply`）。
- 第 2 版：待第一关复核。
