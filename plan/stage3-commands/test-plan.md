# Stage 3 划分第二批：plan／finalize／overview 命令（测试计划）

## 版本、来源与状态

- 对应执行计划：[implementation-plan.md](implementation-plan.md)，计划第 1 版（待审核）。
- Requirement revision: 第 1 版（2026-10-20 负责人要求；同一系列见 PR #95–#118）。
- Target repository revision: 工作分支 `refactor-stage3-commands`；对照基准为父分支 `refactor-stage3-validation`（#118）的 head，命令里用 `git rev-parse origin/refactor-stage3-validation` 动态取（当前 `e303a1c`）。
- Test plan revision: 第 2 版。
- Proposed review status: 待审核。
- 测试范围依据：`Test Engineer Rule.md`。

## 必测清单

| 编号 | 业务目标 | 输入 / 场景 | 预期结果 | 检查方式 |
| --- | --- | --- | --- | --- |
| T0 | 模块可编译、可加载，工厂契约与别名顺序正确（R1、R3、R4） | 工作树 `scripts/contact_state.py`、`scripts/_stage3_commands.py` | 两文件 `py_compile` 成功；`--help` 退出码 0；`build()` 的 keyword-only 参数**精确等于** 56 个名字集合、无位置参数且无默认值；返回 4 个成员；runner 有 4 个同名别名；绑定调用与 4 个别名都在 `canonical_professor_dir` 之后；模块不导入 runner（含 from-import 名）、无动态加载、不碰 `sys.path`／`sys.modules`；4 个名字不再在 runner 顶层定义 | 第 1 步命令；5 条 `T0 ... OK` + 1 条 `T0 CHECKS PASS` |
| T1 | 4 个定义确实离开 runner 顶层、进入模块 `build()`（R1） | 对照基准（父分支 head 导出的 `scripts`）与工作树 `scripts` | `T0`：base 与 head 是两个不同目录、base 仍定义这 4 个、head 一个都不定义；`T1`：模块存在；4 个定义逐个“runner 顶层已无 / 模块 `build()` 内有” | 第 2 步对比脚本的 `T0`／`T1` 行，共 12 条 `OK` |
| T2 | 搬移没有改变任何逻辑（R2） | 同上两侧源码 | 4 个定义的代码 AST 与基准完全相同（脚本忽略 docstring）；docstring 单独核对：2 个有（都多行）清洗后同文、2 个原本没有；runner 其余顶层定义不变；离开 runner 的定义正好是这 4 个；4 个名字都有别名 | 同一脚本的 `T2` 行（7 条 `OK`）；docstring 用第 2 步第二段 |
| T3 | 旧接口与加载方式不变（R3、R4、R5） | 同一进程内分别按文件路径加载两侧 runner；再以子进程直接执行改动后的 runner | 4 个名字在两侧都可调用、`inspect.signature` 相同；`--help` 与父提交逐字节相同；runner 用 `Path(__file__).with_name("_stage3_commands.py")` 加载；56 个实参与参数同名同集合、4 个别名都在调用之后 | 同一脚本的 `T3` 行（9 条 `OK`）、第 1 步的源码约束核对、第 2 步的 `diff -u`；合计 **28 条 `OK`**、末尾 `ALL CHECKS PASS` |
| T4 | `stage3-plan`／`stage3-finalize`／`stage3-rebuild-overview` 与 scoped selection 的行为不变（R2） | 10 个既有方法（均经真实 CLI 子进程）：`test_contact_state.TestRunnerBasics` 的 7 个（`test_04_profile_change_invalidates_stage3_not_stage2`、`test_05_missing_packs_need_refresh`、`test_05b_collection_key_limits_stage3`、`test_05c_scoped_stage3_refresh_preserves_other_state`、`test_05d_scoped_stage3_rejects_six_generated_candidates`、`test_05e_overview_manual_edit_does_not_block_local_finalize`、`test_09_missing_result_keeps_state`）；`test_contact_state.Issue67AdjacentStateTests` 的 2 个（`test_01_stage3_selected_refresh_scopes_from_the_professor_local_selection`、`test_03_scoped_finalize_with_the_local_selection_keeps_other_directions`）；`test_issue66_stage3_local_state.Issue66LocalStateTests.test_rebuild_overview_uses_professor_local_states_and_rebuilds_deleted_projection` | **条件式通过条件**：10 个方法全部 `ok` 则 T4 通过；有失败时按第 5 步在父提交上只对照**同一个失败方法**。注意 `test_04` 内含 `stage4-finalize`、`test_05` 内含 `stage5-plan` 的断言，失败时先按单方法对照，不直接算本批回归 | 第 3 步命令；`Ran 10 tests`、`OK`，无 skip／`FAIL`／`ERROR`。输出落 `/tmp/pc-stage11/t4.log` |
| T5 | 复制 runner 的既有夹具仍能加载新模块（R1、R5） | `test_stage5_immutable.TestWrapperKeepsInstalledLayoutLocator.test_finalize_through_wrapper_certifies_installed_layout_checker`、`test_stage5_dualtarget_contract.InstalledSharedSkillsLocatorTests.test_installed_shared_skills_layout_locator_finds_sibling` | 两方法 `OK` 只证明复制布局含 `_stage3_commands.py` 并成功加载（缺文件会在加载阶段报错）；它们的业务断言属 Stage 5，失败时按第 5 步单方法对照，不算本批回归 | 第 4 步命令；`Ran 2 tests`、`OK`，输出落 `/tmp/pc-stage11/t5.log` |

**既有仓库检查（不属于本批业务必测清单）**：仓库 CI 的 4 个 `shards` 与聚合 job `test` 照常执行，结果按运行编号与 head 单独引用；本批不在本地重跑全量套件。

## 执行步骤

准备与执行都在工作树 `/Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage3-commands` 内进行；临时脚本与运行产物放仓库外 `/tmp/pc-stage11`。

1. T0：编译、工厂契约、别名顺序与模块源码约束（同一命令块，`set -e`）。该块放在 0 缩进，`<<'PY'` 的结束行可按原样执行。
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage3-commands
RUN=/tmp/pc-stage11
mkdir -p "$RUN"
uv run --no-project python --version
uv run --no-project python -m py_compile \
  .apm/skills/professor-contact/scripts/contact_state.py \
  .apm/skills/professor-contact/scripts/_stage3_commands.py
uv run --no-project python .apm/skills/professor-contact/scripts/contact_state.py --help >"$RUN/help-head.txt"
uv run --no-project python - <<'PY'
import ast
from pathlib import Path

SCRIPTS = Path(".apm/skills/professor-contact/scripts")
NAMES = ["_stage3_selected_scope_keys", "cmd_stage3_plan", "cmd_stage3_finalize",
         "cmd_stage3_rebuild_overview"]
EXPECTED_PARAMS = set("""atomic_write staged_pair_commit emit fail soft_exit _stage3_args_from_invocation
MANAGED_BY CANDIDATE_STATE_SCHEMA DIRECTION_IDENTITY_VERSION STAGE3_GENERATOR_CONTRACT_VERSION
CANDIDATE_STATE_KIND INPUT_PACK CANDIDATE_STATE CANDIDATES_MD CANDIDATES_OVERVIEW SELECTION_FILE
REFRESH_SCOPES QUOTE_INPUT_CHARS TRANSLATION_INPUT_CHARS now_utc sha256_text sha256_obj read_json_file
require_professor_dir_under_program truncate rel_path safe_result_file direction_machine_id direction_papers
render_frontmatter split_frontmatter managed_conflict load_input_pack load_candidate_state
strict_candidate_state profile_fingerprint load_profile_text _direction_slices _cross_group_fresh
_parse_direction_id_list _parse_cross_groups STAGE3_INVOCATION_VERSION stage3_validation_evidence
stage3_correction_scopes stage3_repairable_correction_directions carry_stage3_validator
stage3_current_result require_stage3_correction_invariants _write_stage3_invocation
_read_stage3_invocation _require_invocation_source validate_candidate_result validate_cross_result
render_candidates_md render_candidates_overview canonical_professor_dir""".split())

runner_src = (SCRIPTS / "contact_state.py").read_text()
runner = ast.parse(runner_src)
module = ast.parse((SCRIPTS / "_stage3_commands.py").read_text())

build = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == "build")
args = {a.arg for a in build.args.kwonlyargs}
assert args == EXPECTED_PARAMS, (len(args), sorted(EXPECTED_PARAMS - args), sorted(args - EXPECTED_PARAMS))
assert not build.args.args and not build.args.posonlyargs and not build.args.vararg and not build.args.kwarg
assert all(d is None for d in build.args.kw_defaults), build.args.kw_defaults
returned = next(n for n in ast.walk(build) if isinstance(n, ast.Return)
                and isinstance(n.value, ast.Call) and ast.unparse(n.value.func).endswith("SimpleNamespace"))
members = [k.arg for k in returned.value.keywords]
assert len(members) == 4 and set(members) == set(NAMES), members
print("T0 build takes exactly the 56 keyword-only parameters and returns 4 members OK")

aliases = [n for n in runner.body if isinstance(n, ast.Assign)
           and isinstance(n.targets[0], ast.Name)
           and ast.unparse(n.value).startswith("_stage3_commands.")]
assert len(aliases) == 4 and {n.targets[0].id for n in aliases} == set(NAMES)
assert all(ast.unparse(n.value) == "_stage3_commands." + n.targets[0].id for n in aliases)
print("T0 runner has the 4 same-name _stage3_commands aliases OK")

call = next(n for n in runner.body if isinstance(n, ast.Assign)
            and ast.unparse(n.targets[0]) == "_stage3_commands" and isinstance(n.value, ast.Call))
assert sorted(k.arg for k in call.value.keywords) == sorted(EXPECTED_PARAMS)
assert all(ast.unparse(k.value) == k.arg for k in call.value.keywords)
canonical = next(n for n in runner.body if isinstance(n, ast.FunctionDef) and n.name == "canonical_professor_dir")
assert call.lineno > canonical.end_lineno, (canonical.end_lineno, call.lineno)
assert all(a.lineno > call.end_lineno for a in aliases)
print("T0 binding and all 4 aliases sit after canonical_professor_dir OK")

assert 'Path(__file__).with_name("_stage3_commands.py")' in runner_src
imported = {a.name for n in module.body if isinstance(n, ast.Import) for a in n.names}
imported |= {n.module or "" for n in module.body if isinstance(n, ast.ImportFrom)}
assert not any("contact_state" in name for name in imported), sorted(imported)
assert not any("contact_state" in (n.module or "") or any("contact_state" in a.name for a in n.names)
               for n in module.body if isinstance(n, ast.ImportFrom))
dotted = {ast.unparse(n) for n in ast.walk(module) if isinstance(n, ast.Attribute)}
assert not (dotted & {"sys.path", "sys.modules"}), sorted(dotted & {"sys.path", "sys.modules"})
dynamic = {"spec_from_file_location", "module_from_spec", "exec_module", "import_module"}
assert not {d for d in dotted if d.split(".")[-1] in dynamic}, sorted(dotted)
from_names = {a.name for n in module.body if isinstance(n, ast.ImportFrom) for a in n.names}
assert not (from_names & dynamic), sorted(from_names & dynamic)
names_used = {n.id for n in ast.walk(module) if isinstance(n, ast.Name)}
assert not (names_used & {"__import__", "exec", "eval"}), sorted(names_used & {"__import__", "exec", "eval"})
print("T0 runner loads it by path, and the module has no runner import and no dynamic-import names OK")

assert [n for n in runner.body if isinstance(n, ast.FunctionDef) and n.name in NAMES] == []
print("T0 none of the 4 names is defined at runner top level OK")
print("T0 CHECKS PASS")
PY
```
预期：`py_compile` 与 `--help` 无输出、退出码 0；脚本打印 5 条 `T0 ... OK` 与 1 条 `T0 CHECKS PASS`（脚本 6 行，日志首行还有一行 `Python 3.14.6`）。运行该块时把输出重定向到日志：`bash blk0.sh > /tmp/pc-stage11/t0.log 2>&1`（与第 3、4 步一致）。

2. T1–T3：取出对照基准、比对 `--help`、运行对比脚本与 docstring 核对：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage3-commands
RUN=/tmp/pc-stage11
rm -rf "$RUN/base"
mkdir -p "$RUN/base"
BASE_SHA=$(git rev-parse origin/refactor-stage3-validation)
git archive "$BASE_SHA" .apm/skills/professor-contact/scripts | tar -x -C "$RUN/base"
uv run --no-project python "$RUN/base/.apm/skills/professor-contact/scripts/contact_state.py" --help >"$RUN/help-base.txt"
diff -u "$RUN/help-base.txt" "$RUN/help-head.txt"
shasum -a 256 /tmp/pc-stage2-tools/compare_stage2_batch_v2.py
uv run --no-project /tmp/pc-stage2-tools/compare_stage2_batch_v2.py \
  "$RUN/base/.apm/skills/professor-contact/scripts" \
  .apm/skills/professor-contact/scripts \
  _stage3_commands _stage3_commands \
  _stage3_selected_scope_keys cmd_stage3_plan cmd_stage3_finalize cmd_stage3_rebuild_overview
```
脚本来源 `/tmp/pc-stage2-tools/compare_stage2_batch_v2.py`，94 行，sha256 `1ba8c0f49346b1fa78c34fbeec4d82cdab206ebef6cbf1b629769f9e5e4346b6`。
预期：`diff` 无输出；28 条 `OK`（`T0` 3、`T1` 9、`T2` 7、`T3` 9），末尾 `ALL CHECKS PASS`，退出码 0。

   随后做 docstring 核对（只读，必须核对整行摘要）：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage3-commands
RUN=/tmp/pc-stage11
shasum -a 256 /tmp/pc-stage2-tools/check_docstrings_v3.py
uv run --no-project /tmp/pc-stage2-tools/check_docstrings_v3.py \
  "$RUN/base/.apm/skills/professor-contact/scripts" \
  .apm/skills/professor-contact/scripts \
  contact_state.py _stage3_commands.py \
  _stage3_selected_scope_keys cmd_stage3_plan cmd_stage3_finalize cmd_stage3_rebuild_overview
```
脚本 `/tmp/pc-stage2-tools/check_docstrings_v3.py`，109 行，sha256 `31c8b2081c5d1f5398d197d2992084f371d978d99084207a7a9e7f2880f29d4a`。
预期：整行 `total=4 with_doc=2 multi=2 clean_equal=2 without_doc=2 missing=0 mismatched=0` 与末行 `DOCSTRING CHECKS PASS`，退出码 0。

3. T4：只跑清单列出的 10 个方法：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage3-commands/.apm/skills/professor-contact/tests
uv run --no-project python -m unittest \
  test_contact_state.TestRunnerBasics.test_04_profile_change_invalidates_stage3_not_stage2 \
  test_contact_state.TestRunnerBasics.test_05_missing_packs_need_refresh \
  test_contact_state.TestRunnerBasics.test_05b_collection_key_limits_stage3 \
  test_contact_state.TestRunnerBasics.test_05c_scoped_stage3_refresh_preserves_other_state \
  test_contact_state.TestRunnerBasics.test_05d_scoped_stage3_rejects_six_generated_candidates \
  test_contact_state.TestRunnerBasics.test_05e_overview_manual_edit_does_not_block_local_finalize \
  test_contact_state.TestRunnerBasics.test_09_missing_result_keeps_state \
  test_contact_state.Issue67AdjacentStateTests.test_01_stage3_selected_refresh_scopes_from_the_professor_local_selection \
  test_contact_state.Issue67AdjacentStateTests.test_03_scoped_finalize_with_the_local_selection_keeps_other_directions \
  test_issue66_stage3_local_state.Issue66LocalStateTests.test_rebuild_overview_uses_professor_local_states_and_rebuilds_deleted_projection \
  -v > /tmp/pc-stage11/t4.log 2>&1
cat /tmp/pc-stage11/t4.log
```
预期：`Ran 10 tests`、全部 `ok`；无 `skipped`／`FAIL`／`ERROR`。输出落 `/tmp/pc-stage11/t4.log`；若出现失败，先把该日志另存为 `t4-fail-<时间戳>.log` 再重跑，保留每一次正式尝试。

4. T5：只跑清单列出的 2 个夹具方法：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage3-commands/.apm/skills/professor-contact/tests
uv run --no-project python -m unittest \
  test_stage5_immutable.TestWrapperKeepsInstalledLayoutLocator.test_finalize_through_wrapper_certifies_installed_layout_checker \
  test_stage5_dualtarget_contract.InstalledSharedSkillsLocatorTests.test_installed_shared_skills_layout_locator_finds_sibling \
  -v > /tmp/pc-stage11/t5.log 2>&1
cat /tmp/pc-stage11/t5.log
```
预期：`Ran 2 tests`、全部 `ok`。输出落 `/tmp/pc-stage11/t5.log`；失败时同样先另存再重跑。

5. 失败处理：T4／T5 有方法失败时，只在父提交上对照**同一个方法**（不重跑整组），每次对照写独立日志、不覆盖既有记录。下面的 `METHOD` 默认值只是示例，**实际执行时必须替换成真正失败的那个方法**：
```sh
set -e
METHOD="${METHOD:-test_contact_state.TestRunnerBasics.test_04_profile_change_invalidates_stage3_not_stage2}"
BASE_SHA=$(git -C /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage3-commands rev-parse origin/refactor-stage3-validation)
BASELINE=/tmp/pc-stage11/base-${BASE_SHA:0:12}
mkdir -p "$BASELINE"
LOG="$BASELINE/baseline-${METHOD##*.}-$(date +%Y%m%d-%H%M%S).log"
if [ ! -d "$BASELINE/.apm/skills/professor-contact/tests" ]; then
  rm -rf "$BASELINE"
  mkdir -p "$BASELINE"
  git -C /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage3-commands archive "$BASE_SHA" | tar -x -C "$BASELINE"
fi
cd "$BASELINE/.apm/skills/professor-contact/tests"
uv run --no-project python -m unittest "$METHOD" -v >"$LOG" 2>&1 || true
cat "$LOG"
```
判据：父提交上同一个方法也失败＝既有失败；父提交通过而工作树失败＝本批回归。日志名带方法短名与时间戳；没有失败时不执行本步。

6. 失败注入：本批不适用。本批只搬移定义，不改事务、回滚、写入顺序或错误通道；必测清单里没有失败注入项。

7. 既有仓库检查（不属于本批必测项，也不作为通过条件）：PR 推送后引用 4 个 `shards` 与聚合 job `test` 的运行编号与结论。

## 不纳入本清单的范围

| 未纳入项 | 原因 |
| --- | --- |
| `validate_candidate_result`／`validate_cross_result`／`render_candidates_*`／`_stage3_args_from_invocation` | 后续批次；本批按引用注入 |
| Stage 4／5 与迁移命令 | 后续批次 |
| 全量套件的本地重跑 | 仓库 CI 已分片执行，不作为本批必测 |
| R6 的空行接缝 | 属实现侧核对（执行计划第 3 步的只读脚本），不单列用例 |

## 修订记录

- 第 1 版：首次提交（含演练实测的 28 条 OK、10＋2 个方法与 docstring 期望值）。
- 第 2 版：按第一关意见补 T4 失败归因、第 3／4 步输出重定向、`posonlyargs` 断言与 T5 说明；按第二关意见补 T0 的 `t0.log` 落盘说明、第 5 步 `METHOD` 必须替换为真实失败方法、T4／T5 失败时先另存日志。

## 审核状态

- 第 1 版：第一关 PASS。
- 第 2 版：第二关 PASS（已补 `t0.log` 落盘、`METHOD` 替换说明、失败日志另存约定）。
