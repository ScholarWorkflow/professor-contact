# Stage 5 划分第一批：输入发现与候选选择（测试计划）

## 版本、来源与状态

- 对应执行计划：[implementation-plan.md](implementation-plan.md)，计划第 4 版。
- Target repository revision: 工作分支 `refactor-stage5-input`；对照基准为父分支 `refactor-stage3-commands`（#119）的 head，命令里用 `git rev-parse` 动态取（当前 `f8be30d`）。
- Test plan revision: 第 5 版。
- 测试范围依据：`Test Engineer Rule.md`。

## 必测清单

| 编号 | 业务目标 | 输入 / 场景 | 预期结果 | 检查方式 |
| --- | --- | --- | --- | --- |
| T0 | 模块可编译、可加载，工厂契约与别名顺序正确（R1、R3、R4） | 工作树 `scripts/contact_state.py`、`scripts/_stage5_input.py` | `py_compile` 成功；`--help` 退出码 0；`build()` 参数精确等于 11 个名字、无位置参数无默认值；返回 13 个成员；13 个同名别名；绑定调用与别名都早于 `cmd_stage5_plan`；模块不导入 runner、无动态加载、不碰 `sys.path`／`sys.modules`；13 个名字不再在 runner 顶层定义 | 第 1 步命令；5 条 `T0 ... OK` + 1 条 `T0 CHECKS PASS` |
| T1 | 13 个定义确实离开 runner 顶层（R1） | 对照基准与工作树 | base 仍定义 13 个、head 一个都不定义；模块存在；逐个“runner 已无 / 模块 `build()` 内有” | 第 2 步脚本的 `T0`／`T1` 行，共 30 条 `OK` |
| T2 | 搬移没有改变逻辑（R2） | 两侧源码 | 13 个定义的 AST 完全相同；docstring 10 个有（全多行）清洗后同文、3 个原本没有；runner 其余顶层定义不变；离开的是这 13 个；13 个都有别名 | 同一脚本的 `T2` 行（16 条 `OK`）+ docstring 段 |
| T3 | 旧接口与加载方式不变（R3、R4、R5） | 两侧 runner | 13 个名字都可调用、签名相同；`--help` 逐字节相同；用 `Path(__file__).with_name("_stage5_input.py")` 加载；11 个实参同名同集合、13 个别名在调用之后 | 同一脚本的 `T3` 行（27 条 `OK`）；`Path(__file__).with_name` 加载、11 个实参与别名顺序由第 1 步的 T0 脚本核对；合计 **73 条 `OK`**、`ALL CHECKS PASS` |
| T4 | `stage5-list-inputs` 与 plan／finalize 路径上的搬移函数行为不变（R2） | 10 个既有方法：`TestStage5ListInputDiscovery` 的 3 个（`test_valid_and_escaped_packs_produce_one_json_document`、`test_exact_professor_filter_preserves_matching_row_and_read_only_state`、`test_missing_professor_returns_needs_input_without_writes`）；`TestStage5` 的 7 个（`test_stage5_full_flow_and_fact_card`、`test_stage5_requires_user_template`、`test_stage5_choices_id_mapping_fails_closed`、`test_stage5_choices_cannot_replace_the_verified_recipient`、`test_stage5_multiple_emails_use_distinct_files`、`test_stage5_both_outputs_followup_reuses_facts_and_date`、`test_stage5_requires_explicit_user_choices`） | **条件式通过条件**：10 个方法全部 `ok` 则通过；有失败时按第 5 步只对照**同一个失败方法**。注意这些方法同时驱动 `stage5-plan`／`stage5-finalize`，其中 `test_stage5_full_flow_and_fact_card` 与 `test_stage5_both_outputs_followup_reuses_facts_and_date` 还调 `stage5-record-validation`、`test_stage5_multiple_emails_use_distinct_files` 还调 `stage5-rebuild-overview`（都是第二批判据），失败时先单方法对照，不直接算本批回归。**已知限制**：`test_stage5_requires_user_template` 与 `test_stage5_requires_explicit_user_choices` 主要断言 plan 的 `template_error`／`missing_user_choice`，搬移函数只是先执行，属冒烟覆盖；`stage5_partition_pack_spec` 与 `cmd_stage5_partition_choices`（202 行）没有既有行为用例（`grep -rn "stage5-partition-choices" .apm/skills/professor-contact/tests` 为空），只有 T2 的 AST 等价（T1/T3 佐证位置与接口）；要补用例需验收决定人批准，本批不扩范围 | 第 3 步命令；`Ran 10 tests`、`OK`。输出落 `/tmp/pc-stage12/t4.log` |
| T5 | 复制 runner 的既有夹具仍能加载新模块（R1、R5） | `test_stage5_immutable.TestWrapperKeepsInstalledLayoutLocator.test_finalize_through_wrapper_certifies_installed_layout_checker`、`test_stage5_dualtarget_contract.InstalledSharedSkillsLocatorTests.test_installed_shared_skills_layout_locator_finds_sibling` | 两方法 `OK` 只证明复制布局含 `_stage5_input.py` 并成功加载；业务断言属 Stage 5，失败时单方法对照 | 第 4 步命令；`Ran 2 tests`、`OK`。输出落 `/tmp/pc-stage12/t5.log` |

**既有仓库检查（不属于本批业务必测清单）**：仓库 CI 的 4 个 `shards` 与聚合 job `test` 照常执行，不作为通过条件。

## 执行步骤

1. T0（编译、工厂契约、别名顺序、模块源码约束）：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage5-input
RUN=/tmp/pc-stage12
mkdir -p "$RUN"
uv run --no-project python --version
uv run --no-project python -m py_compile \
  .apm/skills/professor-contact/scripts/contact_state.py \
  .apm/skills/professor-contact/scripts/_stage5_input.py
uv run --no-project python .apm/skills/professor-contact/scripts/contact_state.py --help >"$RUN/help-head.txt"
uv run --no-project python - <<'PY'
import ast
from pathlib import Path

SCRIPTS = Path(".apm/skills/professor-contact/scripts")
NAMES = ["stage5_output_peers", "stage5_output_paths", "stage5_output_id", "select_stage5_email",
         "stage5_mode", "stage5_pack_owner", "stage5_local_pack", "stage5_choices_rows",
         "stage5_choices_by_id", "stage5_list_input_rows", "cmd_stage5_list_inputs",
         "stage5_partition_pack_spec", "cmd_stage5_partition_choices"]
EXPECTED_PARAMS = set("""emit fail soft_exit STAGE4_LOCAL_SCHEMA EMAIL_PACK_KIND EMAIL_PACK sha256_text
read_json_file professor_dir_containment_error require_professor_dir_under_program filename_component""".split())

runner_src = (SCRIPTS / "contact_state.py").read_text()
runner = ast.parse(runner_src)
module = ast.parse((SCRIPTS / "_stage5_input.py").read_text())

build = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == "build")
args = {a.arg for a in build.args.kwonlyargs}
assert args == EXPECTED_PARAMS, (sorted(args), sorted(EXPECTED_PARAMS - args), sorted(args - EXPECTED_PARAMS))
assert not build.args.args and not build.args.posonlyargs and not build.args.vararg and not build.args.kwarg
assert all(d is None for d in build.args.kw_defaults), build.args.kw_defaults
returned = next(n for n in ast.walk(build) if isinstance(n, ast.Return)
                and isinstance(n.value, ast.Call) and ast.unparse(n.value.func).endswith("SimpleNamespace"))
members = [k.arg for k in returned.value.keywords]
assert len(members) == 13 and set(members) == set(NAMES), members
print("T0 build takes exactly the 11 keyword-only parameters and returns 13 members OK")

aliases = [n for n in runner.body if isinstance(n, ast.Assign)
           and isinstance(n.targets[0], ast.Name)
           and ast.unparse(n.value).startswith("_stage5_input.")]
assert len(aliases) == 13 and {n.targets[0].id for n in aliases} == set(NAMES)
assert all(ast.unparse(n.value) == "_stage5_input." + n.targets[0].id for n in aliases)
print("T0 runner has the 13 same-name _stage5_input aliases OK")

call = next(n for n in runner.body if isinstance(n, ast.Assign)
            and ast.unparse(n.targets[0]) == "_stage5_input" and isinstance(n.value, ast.Call))
assert sorted(k.arg for k in call.value.keywords) == sorted(EXPECTED_PARAMS)
assert all(ast.unparse(k.value) == k.arg for k in call.value.keywords)
plan_cmd = next(n for n in runner.body if isinstance(n, ast.FunctionDef) and n.name == "cmd_stage5_plan")
assert call.lineno < plan_cmd.lineno, (call.lineno, plan_cmd.lineno)
assert all(a.lineno > call.end_lineno for a in aliases)
assert all(a.lineno < plan_cmd.lineno for a in aliases)
print("T0 binding and all 13 aliases precede cmd_stage5_plan OK")

assert 'Path(__file__).with_name("_stage5_input.py")' in runner_src
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
assert not (from_names & dynamic), sorted(from_names & dynamic)
names_used = {n.id for n in ast.walk(module) if isinstance(n, ast.Name)}
assert not (names_used & {"__import__", "exec", "eval"}), sorted(names_used & {"__import__", "exec", "eval"})
print("T0 runner loads it by path, and the module has no runner import and no dynamic-import names OK")

assert [n for n in runner.body if isinstance(n, ast.FunctionDef) and n.name in NAMES] == []
print("T0 none of the 13 names is defined at runner top level OK")
print("T0 CHECKS PASS")
PY
```
运行该块时重定向到 `bash blk0.sh > /tmp/pc-stage12/t0.log 2>&1`。
预期：脚本 5 条 `T0 ... OK` + 1 条 `T0 CHECKS PASS`（日志首行还会打印 Python 版本，具体版本随环境）。

2. T1–T3（对照基准、`--help`、A/B、docstring）：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage5-input
RUN=/tmp/pc-stage12
rm -rf "$RUN/base"
mkdir -p "$RUN/base"
BASE_SHA=$(git rev-parse origin/refactor-stage3-commands)
git archive "$BASE_SHA" .apm/skills/professor-contact/scripts | tar -x -C "$RUN/base"
uv run --no-project python "$RUN/base/.apm/skills/professor-contact/scripts/contact_state.py" --help >"$RUN/help-base.txt"
diff -u "$RUN/help-base.txt" "$RUN/help-head.txt"
wc -l /tmp/pc-stage2-tools/compare_stage2_batch_v2.py
shasum -a 256 /tmp/pc-stage2-tools/compare_stage2_batch_v2.py
uv run --no-project /tmp/pc-stage2-tools/compare_stage2_batch_v2.py \
  "$RUN/base/.apm/skills/professor-contact/scripts" \
  .apm/skills/professor-contact/scripts \
  _stage5_input _stage5_input \
  stage5_output_peers stage5_output_paths stage5_output_id select_stage5_email stage5_mode \
  stage5_pack_owner stage5_local_pack stage5_choices_rows stage5_choices_by_id stage5_list_input_rows \
  cmd_stage5_list_inputs stage5_partition_pack_spec cmd_stage5_partition_choices >"$RUN/compare.log" 2>&1
cat "$RUN/compare.log"
```
预期：`diff` 无输出；**73 条 `OK`**（T0 3、T1 27、T2 16、T3 27）、`ALL CHECKS PASS`。输出落 `$RUN/compare.log`（块内已自重定向，外层不要再重定向到同一文件）。

   随后 docstring 核对（必须核对整行摘要；注意本块依赖上一块导出的 `$RUN/base`，单独执行时要先跑第 2 步上半段）：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage5-input
RUN=/tmp/pc-stage12
wc -l /tmp/pc-stage2-tools/check_docstrings_v3.py
shasum -a 256 /tmp/pc-stage2-tools/check_docstrings_v3.py
uv run --no-project /tmp/pc-stage2-tools/check_docstrings_v3.py \
  "$RUN/base/.apm/skills/professor-contact/scripts" \
  .apm/skills/professor-contact/scripts \
  contact_state.py _stage5_input.py \
  stage5_output_peers stage5_output_paths stage5_output_id select_stage5_email stage5_mode \
  stage5_pack_owner stage5_local_pack stage5_choices_rows stage5_choices_by_id stage5_list_input_rows \
  cmd_stage5_list_inputs stage5_partition_pack_spec cmd_stage5_partition_choices >"$RUN/docstring.log" 2>&1
cat "$RUN/docstring.log"
```
预期整行：`total=13 with_doc=10 multi=10 clean_equal=10 without_doc=3 missing=0 mismatched=0` 与 `DOCSTRING CHECKS PASS`。输出落 `$RUN/docstring.log`。

3. T4：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage5-input/.apm/skills/professor-contact/tests
uv run --no-project python -m unittest \
  test_contact_state.TestStage5ListInputDiscovery.test_valid_and_escaped_packs_produce_one_json_document \
  test_contact_state.TestStage5ListInputDiscovery.test_exact_professor_filter_preserves_matching_row_and_read_only_state \
  test_contact_state.TestStage5ListInputDiscovery.test_missing_professor_returns_needs_input_without_writes \
  test_contact_state.TestStage5.test_stage5_full_flow_and_fact_card \
  test_contact_state.TestStage5.test_stage5_requires_user_template \
  test_contact_state.TestStage5.test_stage5_choices_id_mapping_fails_closed \
  test_contact_state.TestStage5.test_stage5_choices_cannot_replace_the_verified_recipient \
  test_contact_state.TestStage5.test_stage5_multiple_emails_use_distinct_files \
  test_contact_state.TestStage5.test_stage5_both_outputs_followup_reuses_facts_and_date \
  test_contact_state.TestStage5.test_stage5_requires_explicit_user_choices \
  -v > /tmp/pc-stage12/t4.log 2>&1
cat /tmp/pc-stage12/t4.log
```
预期：`Ran 10 tests`、全部 `ok`；失败时先另存日志再重跑。

4. T5：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage5-input/.apm/skills/professor-contact/tests
uv run --no-project python -m unittest \
  test_stage5_immutable.TestWrapperKeepsInstalledLayoutLocator.test_finalize_through_wrapper_certifies_installed_layout_checker \
  test_stage5_dualtarget_contract.InstalledSharedSkillsLocatorTests.test_installed_shared_skills_layout_locator_finds_sibling \
  -v > /tmp/pc-stage12/t5.log 2>&1
cat /tmp/pc-stage12/t5.log
```
预期：`Ran 2 tests`、全部 `ok`。

5. 失败处理：只在父提交上对照**同一个失败方法**，日志写进按 SHA 建的目录、按方法短名 + 时间戳命名；`METHOD` 默认值只是示例，实际要替换成真正失败的方法。本轮没有失败方法，演练时只跑了一次作为“块可执行性预检”，不构成失败对照结论。
```sh
set -e
METHOD="${METHOD:-test_contact_state.TestStage5.test_stage5_full_flow_and_fact_card}"
BASE_SHA=$(git -C /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage5-input rev-parse origin/refactor-stage3-commands)
BASELINE=/tmp/pc-stage12/base-${BASE_SHA:0:12}
mkdir -p "$BASELINE"
LOG="$BASELINE/baseline-${METHOD##*.}-$(date +%Y%m%d-%H%M%S).log"
if [ ! -f "$BASELINE/.apm/skills/professor-contact/tests/test_contact_state.py" ]; then
  rm -rf "$BASELINE"
  mkdir -p "$BASELINE"
  git -C /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage5-input archive "$BASE_SHA" | tar -x -C "$BASELINE"
fi
cd "$BASELINE/.apm/skills/professor-contact/tests"
uv run --no-project python -m unittest "$METHOD" -v >"$LOG" 2>&1 || true
cat "$LOG"
```
判据：父提交同一个方法也失败＝既有失败；父提交通过而工作树失败＝本批回归。日志名带方法短名与时间戳；没有失败时不执行本步。

6. 失败注入：本批不适用。本批只把定义搬到同目录模块并保持函数体逐字不变，不改事务、回滚、写入顺序、错误通道或 CLI 参数；必测清单里没有失败注入项，因此不新增。

7. 既有仓库检查：PR 推送后引用 CI 运行编号，不作为通过条件。

## 不纳入本清单的范围

| 未纳入项 | 原因 |
| --- | --- |
| `cmd_stage5_plan`／`cmd_stage5_finalize`／`cmd_stage5_rebuild_overview`／`cmd_stage5_record_validation`／`stage5_recipient_authority`（共 632 行） | 第二批 |
| Stage 4、迁移、剩余共享 helper | 后续批次 |
| 全量套件的本地重跑 | 仓库 CI 已分片执行 |
| R6 的空行接缝 | 属实现侧核对 |

## 修订记录

- 第 1 版：首次提交（含演练实测的 73 条 OK、10＋2 个方法与 docstring 期望值）。
- 第 2 版：按第一关意见修正——T4 目标收窄为“`stage5-list-inputs` 与 plan／finalize 路径”，并写明 partition 命令只有 T1–T3 结构等价的已知限制；T3 行补加载／实参／别名顺序的核对出处；T0 的 import 扫描改用 `ast.walk`；第 2 步补脚本行数与 sha256；失败注入理由写全；第二批命令清单补全。
- 第 3 版：按复核意见收尾——T4 注意句补 `stage5-record-validation`／`stage5-rebuild-overview`；已知限制补“两个 requires_* 方法属冒烟”；grep 路径改为 `.apm/skills/professor-contact/tests`；第 2 步补 docstring 脚本的 `wc -l`／`shasum`；版本指针改成计划第 3 版。
- 第 5 版：按第二关复核的可改进项——版本指针改计划第 4 版；第 2 步补 `compare.log`／`docstring.log` 的落盘与依赖说明；失败处理的目录检查改查 `test_contact_state.py`；注明演练那次 baseline 是块预检。
- 第 4 版：按第一关复核的可改进项调整——record-validation 补 `test_stage5_both_outputs…`；结构等价表述改为“T2 的 AST 等价（T1/T3 佐证）”；T5 用完整类名；日志首行的 Python 版本不再写死；修订记录按版本排序。

## 审核状态

- 第 1 版：第一关 NEEDS_MODIFICATION（T4 声称覆盖 partition 但无用例）。
- 第 2 版：第一关复核提出 1 项残项。
- 第 3 版：第一关复核提出 1 项残项（已修）。
- 第 4 版：第一关 PASS。
- 第 5 版：第二关 PASS。
