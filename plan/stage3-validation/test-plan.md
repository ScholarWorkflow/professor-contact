# Stage 3 划分第一批：校验与报告管线（测试计划）

## 版本、来源与状态

- 对应执行计划：[implementation-plan.md](implementation-plan.md)，计划第 1 版（待审核）。
- Requirement revision: 第 1 版（2026-10-20 负责人要求；同一系列见 PR #95–#117）。
- Target repository revision: 工作分支 `refactor-stage3-validation`；对照基准为父分支 `refactor-input-pack`（#117）的 head，命令里用 `git rev-parse origin/refactor-input-pack` 动态取（当前 `6ff8549`）。
- Test plan revision: 第 2 版。
- Proposed review status: 待审核。
- 测试范围依据：`Test Engineer Rule.md`。

## 必测清单

| 编号 | 业务目标 | 输入 / 场景 | 预期结果 | 检查方式 |
| --- | --- | --- | --- | --- |
| T0 | 模块可编译、可加载，工厂契约与别名顺序正确（R1、R3、R4） | 工作树 `scripts/contact_state.py`、`scripts/_stage3_validation.py` | 两文件 `py_compile` 成功；`--help` 退出码 0；`build()` 的 keyword-only 参数**精确等于** 36 个名字集合、无位置参数；返回 18 个成员且去重后仍 18；runner 有 18 个 `X = _stage3_validation.X` 别名、集合与成员一致；绑定调用与 18 个别名都早于第一个消费方 `cmd_stage3_plan`（`_load_stage3_handoff` 本批已搬走，不能再用它做锚点）；模块不导入 runner、无动态加载、不碰 `sys.path`／`sys.modules`；18 个名字不再在 runner 顶层定义 | 第 1 步命令；5 条 `T0 ... OK` + 1 条 `T0 CHECKS PASS`（共 6 行） |
| T1 | 18 个定义确实离开 runner 顶层、进入模块 `build()`（R1） | 对照基准（父分支 head 导出的 `scripts`）与工作树 `scripts` | `T0`：base 与 head 是两个不同目录、base 仍定义 18 个定义、head 一个都不定义；`T1`：模块存在；18 个定义逐个“runner 顶层已无 / 模块 `build()` 内有” | 第 2 步对比脚本的 `T0 ...`／`T1 ...` 行，共 40 条 `OK` |
| T2 | 搬移没有改变任何逻辑（R2） | 同上两侧源码 | 18 个定义的代码 AST 与基准完全相同（脚本忽略 docstring）；docstring 单独核对：16 个有 docstring（其中 13 个多行）清洗后同文、2 个原本没有；runner 其余顶层定义 AST 不变；离开 runner 的定义正好是这 18 个；18 个名字都有别名 | 同一脚本的 `T2 ...` 行（21 条 `OK`）；docstring 用第 2 步第二段 |
| T3 | 旧接口与加载方式不变（R3、R4、R5） | 同一进程内分别按文件路径加载两侧 runner；再以子进程直接执行改动后的 runner | 18 个名字在两侧都可调用、`inspect.signature` 相同；`--help` 退出码 0 且与父提交逐字节相同；runner 用 `Path(__file__).with_name("_stage3_validation.py")` 加载；36 个实参与参数同名同集合、18 个别名都在调用之后 | 同一脚本的 `T3 ...` 行（37 条 `OK`）、第 1 步的源码约束核对、第 2 步的 `diff -u`；合计 **98 条 `OK`**、末尾 `ALL CHECKS PASS` |
| T4 | 校验记录、prepare/write/save-validation 与渲染绑定的行为不变（R2） | 10 个既有方法（9 个经 CLI 子进程，其中 5 个 handoff 方法覆盖 `stage3-prepare/write/save/record-validation` 四条命令；1 个直接调用 `_stage3_bound_render`）：`test_issue66_validation_handoff.Issue66ValidationHandoffTests` 的 5 个（`test_fixed_writer_save_and_record_preserve_pass_bytes`、`test_fixed_writer_save_and_record_preserve_minor_result`、`test_save_copies_noncanonical_utf8_bytes_and_bad_digest_does_not_advance`、`test_writer_refuses_existing_output_without_replacing_it`、`test_writer_refuses_symlink_output_without_replacing_target`）；`test_contact_state.Issue66RecordedValidationScopeTests` 的 2 个（`test_handoff_record_expands_global_blocker_to_rendered_objects`、`test_rewritten_validation_file_cannot_expand_or_replace_recorded_correction`）；`test_issue66_r12_validation_input_sha.Issue66RecordValidationInputShaTests.test_record_validation_returns_input_bytes_sha`；`test_contact_state.TestRunnerBasics.test_12_stage3_validator_is_persisted_separately`；`test_issue61_direction_credibility_warning.DirectionCredibilityWarningTests.test_warning_is_part_of_the_sha_bound_render`（直接调用 `_stage3_bound_render`） | **条件式通过条件**：10 个方法全部 `ok` 则 T4 通过；有失败时按第 5 步在父提交上只对照**同一个失败方法**。注意 `test_rewritten_validation_file…` 内部会跑 `stage3-plan`／`stage3-finalize`（第二批判据），失败时按单方法对照，不当作本批验收。**已知限制**：`carry_stage3_validator`、`stage3_current_result`、`require_stage3_correction_invariants`、`_paper_refs`、`_stage3_candidates_entry` 没有直接对应用例，但经 record→`stage3_validation_evidence`、plan/finalize 的间接路径覆盖；只有 T2 的 AST 等价是兜底 | 第 3 步命令；`Ran 10 tests`、`OK`，无 skip／`FAIL`／`ERROR` |
| T5 | 复制 runner 的既有夹具仍能加载新模块（R1、R5） | `test_stage5_immutable.TestWrapperKeepsInstalledLayoutLocator.test_finalize_through_wrapper_certifies_installed_layout_checker`、`test_stage5_dualtarget_contract.InstalledSharedSkillsLocatorTests.test_installed_shared_skills_layout_locator_finds_sibling` | 复制布局包含 `_stage3_validation.py`，复制后的 runner 能按路径加载它；两方法 `OK` | 第 4 步命令；两方法 `OK` 即证明复制布局含 `_stage3_validation.py` 并成功加载（缺文件会在 runner 加载 phase 直接报错） |

**既有仓库检查（不属于本批业务必测清单）**：仓库 CI 的 4 个 `shards` 与聚合 job `test` 照常执行，结果按运行编号与 head 单独引用；本批不在本地重跑全量套件。

## 执行步骤

准备与执行都在工作树 `/Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage3-validation` 内进行；临时脚本与运行产物放仓库外 `/tmp/pc-stage10`。

1. T0：编译、工厂契约、别名顺序与模块源码约束（同一命令块，`set -e`）。该块放在 0 缩进，`<<'PY'` 的结束行可按原样执行。
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage3-validation
RUN=/tmp/pc-stage10
mkdir -p "$RUN"
uv run --no-project python --version
uv run --no-project python -m py_compile \
  .apm/skills/professor-contact/scripts/contact_state.py \
  .apm/skills/professor-contact/scripts/_stage3_validation.py
uv run --no-project python .apm/skills/professor-contact/scripts/contact_state.py --help >"$RUN/help-head.txt"
uv run --no-project python - <<'PY'
import ast
from pathlib import Path

SCRIPTS = Path(".apm/skills/professor-contact/scripts")
NAMES = ["_stage3_bound_render", "_stage3_candidates_entry", "stage3_validation_evidence",
         "stage3_correction_scopes", "stage3_repairable_correction_directions",
         "carry_stage3_validator", "stage3_current_result", "_paper_refs",
         "require_stage3_correction_invariants", "_write_stage3_invocation",
         "_read_stage3_invocation", "_require_invocation_source", "_stage3_handoff_directory",
         "_load_stage3_handoff", "cmd_stage3_prepare_validation",
         "cmd_stage3_write_validation", "cmd_stage3_save_validation",
         "cmd_stage3_record_validation"]
EXPECTED_PARAMS = {"atomic_json", "emit", "fail", "soft_exit", "STAGE3_VALIDATION_MAX_ROUNDS",
                   "scope_key", "_stage3_issue_scopes", "_stage3_validation_files",
                   "_stage3_normalized_absolute_path", "_stage3_complete_write_result",
                   "_require_stage3_handoff_round", "_stage3_json_object_pairs",
                   "_stage3_json_reject_constant", "_stage3_write_buffer",
                   "stage3_render_line_scopes", "INPUT_PACK", "CANDIDATE_STATE", "CANDIDATES_MD",
                   "now_utc", "sha256_bytes", "sha256_text", "require_professor_dir_under_program",
                   "split_frontmatter", "load_input_pack", "load_candidate_state",
                   "profile_fingerprint", "STAGE3_INVOCATION_VERSION", "STAGE3_INVOCATION_FILE",
                   "STAGE3_HANDOFF_VERSION", "STAGE3_HANDOFF_ROOT", "STAGE3_HANDOFF_FILE",
                   "STAGE3_VALIDATOR_OUTPUT_FILE", "STAGE3_VALIDATION_TARGET_FILE",
                   "STAGE3_IMMUTABLE_CANDIDATE_FIELDS", "STAGE3_REPAIRABLE_CANDIDATE_FIELDS",
                   "STAGE3_INVOCATION_SOURCE_PARAMS"}

runner_src = (SCRIPTS / "contact_state.py").read_text()
runner = ast.parse(runner_src)
module = ast.parse((SCRIPTS / "_stage3_validation.py").read_text())

build = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == "build")
args = {a.arg for a in build.args.kwonlyargs}
assert args == EXPECTED_PARAMS, (sorted(args), sorted(EXPECTED_PARAMS - args), sorted(args - EXPECTED_PARAMS))
assert not build.args.args and not build.args.vararg and not build.args.kwarg
returned = next(n for n in ast.walk(build) if isinstance(n, ast.Return)
                and isinstance(n.value, ast.Call) and ast.unparse(n.value.func).endswith("SimpleNamespace"))
members = [k.arg for k in returned.value.keywords]
assert len(members) == 18 and len(set(members)) == 18, members
assert set(members) == set(NAMES), sorted(set(NAMES) ^ set(members))
print("T0 build takes exactly the 36 keyword-only parameters and returns 18 members OK")

aliases = [n for n in runner.body if isinstance(n, ast.Assign)
           and isinstance(n.targets[0], ast.Name)
           and ast.unparse(n.value).startswith("_stage3_validation.")]
assert len(aliases) == 18 and len({n.targets[0].id for n in aliases}) == 18
assert {n.targets[0].id for n in aliases} == set(NAMES)
assert all(ast.unparse(n.value) == "_stage3_validation." + n.targets[0].id for n in aliases)
print("T0 runner has the 18 same-name _stage3_validation aliases OK")

call = next(n for n in runner.body if isinstance(n, ast.Assign)
            and ast.unparse(n.targets[0]) == "_stage3_validation" and isinstance(n.value, ast.Call))
assert sorted(k.arg for k in call.value.keywords) == sorted(EXPECTED_PARAMS)
assert all(ast.unparse(k.value) == k.arg for k in call.value.keywords)
# `_load_stage3_handoff` 本批已搬走，用它做锚点会 StopIteration；改以仍在 runner 的
# 第一个消费方 `cmd_stage3_plan` 为界，断言绑定调用与 18 个别名都早于它。
plan = next(n for n in runner.body if isinstance(n, ast.FunctionDef) and n.name == "cmd_stage3_plan")
assert call.lineno < plan.lineno, (call.lineno, plan.lineno)
assert all(a.lineno > call.end_lineno for a in aliases)
assert all(a.lineno < plan.lineno for a in aliases)
print("T0 binding and all 18 aliases precede cmd_stage3_plan OK")

assert 'Path(__file__).with_name("_stage3_validation.py")' in runner_src
imported = {a.name for n in module.body if isinstance(n, ast.Import) for a in n.names}
imported |= {n.module or "" for n in module.body if isinstance(n, ast.ImportFrom)}
assert not any("contact_state" in name for name in imported), sorted(imported)
dotted = {ast.unparse(n) for n in ast.walk(module) if isinstance(n, ast.Attribute)}
assert not (dotted & {"sys.path", "sys.modules"}), sorted(dotted & {"sys.path", "sys.modules"})
dynamic = {"spec_from_file_location", "module_from_spec", "exec_module", "import_module"}
assert not {d for d in dotted if d.split(".")[-1] in dynamic}, sorted(dotted)
from_names = {a.name for n in module.body if isinstance(n, ast.ImportFrom) for a in n.names}
assert not (from_names & dynamic), sorted(from_names & dynamic)
assert not any("contact_state" in (n.module or "") or any("contact_state" in a.name for a in n.names)
               for n in module.body if isinstance(n, ast.ImportFrom))
assert all(d is None for d in build.args.kw_defaults), build.args.kw_defaults
names_used = {n.id for n in ast.walk(module) if isinstance(n, ast.Name)}
assert not (names_used & {"__import__", "exec", "eval"}), sorted(names_used & {"__import__", "exec", "eval"})
print("T0 runner loads it by path, and the module has no runner import and no dynamic-import names OK")

assert [n for n in runner.body if isinstance(n, ast.FunctionDef) and n.name in NAMES] == []
print("T0 none of the 18 names is defined at runner top level OK")
print("T0 CHECKS PASS")
PY
```
预期：`py_compile` 与 `--help` 无输出、退出码 0；脚本打印 5 条 `T0 ... OK` 与 1 条 `T0 CHECKS PASS`（脚本输出 6 行，日志首行还有一行 `Python 3.14.6`）。

2. T1–T3：取出对照基准、比对 `--help`、运行对比脚本与 docstring 核对：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage3-validation
RUN=/tmp/pc-stage10
rm -rf "$RUN/base"
mkdir -p "$RUN/base"
BASE_SHA=$(git rev-parse origin/refactor-input-pack)
git archive "$BASE_SHA" .apm/skills/professor-contact/scripts | tar -x -C "$RUN/base"
uv run --no-project python "$RUN/base/.apm/skills/professor-contact/scripts/contact_state.py" --help >"$RUN/help-base.txt"
diff -u "$RUN/help-base.txt" "$RUN/help-head.txt"
shasum -a 256 /tmp/pc-stage2-tools/compare_stage2_batch_v2.py
uv run --no-project /tmp/pc-stage2-tools/compare_stage2_batch_v2.py \
  "$RUN/base/.apm/skills/professor-contact/scripts" \
  .apm/skills/professor-contact/scripts \
  _stage3_validation _stage3_validation \
  _stage3_bound_render _stage3_candidates_entry stage3_validation_evidence stage3_correction_scopes \
  stage3_repairable_correction_directions carry_stage3_validator stage3_current_result _paper_refs \
  require_stage3_correction_invariants _write_stage3_invocation _read_stage3_invocation \
  _require_invocation_source _stage3_handoff_directory _load_stage3_handoff \
  cmd_stage3_prepare_validation cmd_stage3_write_validation cmd_stage3_save_validation \
  cmd_stage3_record_validation
```
脚本来源 `/tmp/pc-stage2-tools/compare_stage2_batch_v2.py`，94 行，sha256 `1ba8c0f49346b1fa78c34fbeec4d82cdab206ebef6cbf1b629769f9e5e4346b6`。
预期：`diff` 无输出；98 条 `OK`（`T0` 3、`T1` 37、`T2` 21、`T3` 37），末尾 `ALL CHECKS PASS`，退出码 0。

   随后做 docstring 核对（只读，必须核对整行摘要）：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage3-validation
RUN=/tmp/pc-stage10
shasum -a 256 /tmp/pc-stage2-tools/check_docstrings_v3.py
uv run --no-project /tmp/pc-stage2-tools/check_docstrings_v3.py \
  "$RUN/base/.apm/skills/professor-contact/scripts" \
  .apm/skills/professor-contact/scripts \
  contact_state.py _stage3_validation.py \
  _stage3_bound_render _stage3_candidates_entry stage3_validation_evidence stage3_correction_scopes \
  stage3_repairable_correction_directions carry_stage3_validator stage3_current_result _paper_refs \
  require_stage3_correction_invariants _write_stage3_invocation _read_stage3_invocation \
  _require_invocation_source _stage3_handoff_directory _load_stage3_handoff \
  cmd_stage3_prepare_validation cmd_stage3_write_validation cmd_stage3_save_validation \
  cmd_stage3_record_validation
```
脚本 `/tmp/pc-stage2-tools/check_docstrings_v3.py`，109 行，sha256 `31c8b2081c5d1f5398d197d2992084f371d978d99084207a7a9e7f2880f29d4a`。
预期：整行 `total=18 with_doc=16 multi=13 clean_equal=16 without_doc=2 missing=0 mismatched=0` 与末行 `DOCSTRING CHECKS PASS`，退出码 0。脚本对“base 有、head 丢失”只把 `without_doc` 加一、退出码仍为 0，所以必须核对整行摘要。

3. T4：只跑清单列出的 10 个方法：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage3-validation/.apm/skills/professor-contact/tests
uv run --no-project python -m unittest \
  test_issue66_validation_handoff.Issue66ValidationHandoffTests.test_fixed_writer_save_and_record_preserve_pass_bytes \
  test_issue66_validation_handoff.Issue66ValidationHandoffTests.test_fixed_writer_save_and_record_preserve_minor_result \
  test_issue66_validation_handoff.Issue66ValidationHandoffTests.test_save_copies_noncanonical_utf8_bytes_and_bad_digest_does_not_advance \
  test_issue66_validation_handoff.Issue66ValidationHandoffTests.test_writer_refuses_existing_output_without_replacing_it \
  test_issue66_validation_handoff.Issue66ValidationHandoffTests.test_writer_refuses_symlink_output_without_replacing_target \
  test_contact_state.Issue66RecordedValidationScopeTests.test_handoff_record_expands_global_blocker_to_rendered_objects \
  test_contact_state.Issue66RecordedValidationScopeTests.test_rewritten_validation_file_cannot_expand_or_replace_recorded_correction \
  test_issue66_r12_validation_input_sha.Issue66RecordValidationInputShaTests.test_record_validation_returns_input_bytes_sha \
  test_contact_state.TestRunnerBasics.test_12_stage3_validator_is_persisted_separately \
  test_issue61_direction_credibility_warning.DirectionCredibilityWarningTests.test_warning_is_part_of_the_sha_bound_render \
  -v
```
预期：`Ran 10 tests`、全部 `ok`；无 `skipped`／`FAIL`／`ERROR`。输出落 `/tmp/pc-stage10/t4.log`。

4. T5：只跑清单列出的 2 个夹具方法：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage3-validation/.apm/skills/professor-contact/tests
uv run --no-project python -m unittest \
  test_stage5_immutable.TestWrapperKeepsInstalledLayoutLocator.test_finalize_through_wrapper_certifies_installed_layout_checker \
  test_stage5_dualtarget_contract.InstalledSharedSkillsLocatorTests.test_installed_shared_skills_layout_locator_finds_sibling \
  -v
```
预期：`Ran 2 tests`、全部 `ok`。输出落 `/tmp/pc-stage10/t5.log`。

5. 失败处理：T4／T5 有方法失败时，只在父提交上对照**同一个方法**（不重跑整组），每次对照写独立日志、不覆盖既有记录。下面的块用 `METHOD` 环境变量指定方法，未指定时跑示例里那一个：
```sh
set -e
METHOD="${METHOD:-test_issue66_validation_handoff.Issue66ValidationHandoffTests.test_fixed_writer_save_and_record_preserve_pass_bytes}"
BASE_SHA=$(git -C /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage3-validation rev-parse origin/refactor-input-pack)
BASELINE=/tmp/pc-stage10/base-${BASE_SHA:0:12}
LOG="$BASELINE/baseline-${METHOD##*.}-$(date +%Y%m%d-%H%M%S).log"
mkdir -p "$BASELINE"
if [ ! -d "$BASELINE/.apm/skills/professor-contact/tests" ]; then
  git -C /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage3-validation archive "$BASE_SHA" | tar -x -C "$BASELINE"
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
| `cmd_stage3_plan`／`cmd_stage3_finalize`／`cmd_stage3_rebuild_overview`／`_stage3_selected_scope_keys` | 第二批 |
| Stage 4／5 与迁移命令 | 后续批次 |
| 全量套件的本地重跑 | 仓库 CI 已分片执行，不作为本批必测 |
| 新模块单独的可导入性单测 | T0 的直接执行、T3 的按路径加载与 T5 的复制加载已覆盖真实加载方式 |
| R6 的空行接缝 | 属实现侧核对（执行计划第 3 步的只读脚本），不单列用例 |

## 修订记录

- 第 1 版：首次提交。
- 第 2 版：按第一关意见修正——T4 换掉 5 个只读 `SKILL.md` 的静态方法与 1 个断言第二批 `cmd_stage3_rebuild_overview` 的方法，改成 8 个真正驱动 `stage3-prepare/write/save/record-validation` 的方法 + 1 个直接调用 `_stage3_bound_render` 的方法 + 1 个 record 方法；目标改成“校验记录、prepare/write/save-validation 与渲染绑定”；补已知限制（5 个定义只有 AST 覆盖）；T0 补 `from-import` 与 `kw_defaults` 断言；第 5 步日志移进基准目录、示例方法换成新的；T5 预期补“先确认复制布局含新模块”。换用新 T4 后演练立刻暴露模块缺 `os`/`sys`/`tempfile` 三个 import（prepare/write/save 一跑就 `NameError`），已在实现侧修正。

## 审核状态

- 第 1 版：第一关 NEEDS_MODIFICATION（T4 有 5 个只读 SKILL.md 的方法、1 个断言第二批判据、目标与覆盖不符）。
- 第 2 版：第一关 PASS；第二关 PASS（已按复核意见清理基准目录、统一 `$RUN/base`、修正条数措辞、加测试目录守卫、补 T4 归因说明与日志落盘位置）。
