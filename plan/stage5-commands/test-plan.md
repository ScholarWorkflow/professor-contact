# Stage 5 划分第二批：计划、终稿与概览命令（测试计划）

## 版本、来源与状态

- 对应执行计划：[implementation-plan.md](implementation-plan.md)，计划第 3 版。
- Target repository revision: 工作分支 `refactor-stage5-commands`；对照基准为父分支 `refactor-stage5-input`（#120）的 head，命令里用 `git rev-parse` 动态取（当前 `ce46f36`）。
- Test plan revision: 第 3 版。
- 测试范围依据：`Test Engineer Rule.md`。

## 必测清单

| 编号 | 业务目标 | 输入 / 场景 | 预期结果 | 检查方式 |
| --- | --- | --- | --- | --- |
| T0 | 模块可编译、可加载，工厂契约与别名顺序正确（R1、R3、R4） | 工作树 `scripts/contact_state.py`、`scripts/_stage5_commands.py` | `py_compile` 成功；`--help` 退出码 0；`build()` 参数精确等于 51 个名字、无位置参数无默认值；返回 5 个成员；5 个同名别名；绑定调用与别名都在 `render_fact_check_card` 之后；模块不导入 runner（含 from-import 名）、无动态加载、不碰 `sys.path`／`sys.modules`；5 个名字不再在 runner 顶层定义 | 第 1 步命令；5 条 `T0 ... OK` + 1 条 `T0 CHECKS PASS` |
| T1 | 5 个定义确实离开 runner 顶层（R1） | 对照基准与工作树 | base 仍定义 5 个、head 一个都不定义；模块存在；逐个“runner 已无 / 模块 `build()` 内有” | 第 2 步脚本的 `T0`／`T1` 行，共 14 条 `OK` |
| T2 | 搬移没有改变逻辑（R2） | 两侧源码 | 5 个定义的 AST 完全相同；docstring 2 个有（都多行）清洗后同文、3 个原本没有；runner 其余**函数/类定义**不变（脚本的 `top_defs` 只比函数与类，不含顶层常量）；离开的是这 5 个；5 个都有别名 | 同一脚本的 `T2` 行（8 条 `OK`）+ docstring 段 |
| T3 | 旧接口与加载方式不变（R3、R4、R5） | 两侧 runner | 5 个名字都可调用、签名相同；`--help` 逐字节相同；用 `Path(__file__).with_name("_stage5_commands.py")` 加载；51 个实参同名同集合、5 个别名在调用之后 | 同一脚本的 `T3` 行（11 条 `OK`）+ 第 1 步的源码约束核对；合计 **33 条 `OK`**、`ALL CHECKS PASS` |
| T4 | `stage5-plan`／`stage5-finalize`／`stage5-rebuild-overview`／`stage5-record-validation` 的行为不变（R2） | 10 个既有方法（均经真实 CLI 子进程）：`test_contact_state.TestStage5` 的 6 个（`test_stage5_full_flow_and_fact_card`、`test_stage5_both_outputs_followup_reuses_facts_and_date`、`test_stage5_multiple_emails_use_distinct_files`、`test_stage5_batch_failure_does_not_write_first_email`、`test_humanizer_lost_title_rejected`、`test_stage5_checklist_header_row_matches_body_salutation`）；`test_contact_state.TestStage5.test_stage5_finalize_gate_stops_before_the_choices_file_is_read`、`test_contact_state.TestStage5.test_stage5_requires_user_template`、`test_contact_state.TestStage5.test_stage5_choices_id_mapping_fails_closed`、`test_contact_state.TestStage5TargetedEmailScope.test_issue59_t59_5_batch_mode_still_validates_every_pack_row` | **条件式通过条件**：10 个方法全部 `ok` 则通过；有失败时按第 5 步只对照**同一个失败方法**。四条命令的覆盖分布：`stage5-plan` 与 `stage5-finalize` 各由 6 个以上方法驱动，`stage5-rebuild-overview` 由 `multiple_emails` 与 `issue59_t59_5` 驱动，`stage5-record-validation` 由 `full_flow` 与 `both_outputs` 驱动；这些方法也会走到第一批搬走的 `stage5_local_pack`／`stage5_mode`，失败时先单方法对照，不直接算本批回归 | 第 3 步命令；`Ran 10 tests`、`OK`。输出落 `/tmp/pc-stage13/t4.log` |
| T5 | 复制 runner 的既有夹具仍能加载新模块（R1、R5） | `test_stage5_immutable.TestWrapperKeepsInstalledLayoutLocator.test_finalize_through_wrapper_certifies_installed_layout_checker`、`test_stage5_dualtarget_contract.InstalledSharedSkillsLocatorTests.test_installed_shared_skills_layout_locator_finds_sibling` | 两方法 `OK` 只证明复制布局含 `_stage5_commands.py` 并成功加载；业务断言属 Stage 5，失败时单方法对照 | 第 4 步命令；`Ran 2 tests`、`OK`。输出落 `/tmp/pc-stage13/t5.log` |

**既有仓库检查（不属于本批业务必测清单）**：仓库 CI 的 4 个 `shards` 与聚合 job `test` 照常执行，不作为通过条件。

## 执行步骤

1. T0（编译、工厂契约、别名顺序、模块源码约束）：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage5-commands
RUN=/tmp/pc-stage13
mkdir -p "$RUN"
uv run --no-project python --version
uv run --no-project python -m py_compile \
  .apm/skills/professor-contact/scripts/contact_state.py \
  .apm/skills/professor-contact/scripts/_stage5_commands.py
uv run --no-project python .apm/skills/professor-contact/scripts/contact_state.py --help >"$RUN/help-head.txt"
uv run --no-project python - <<'PY'
import ast
from pathlib import Path

SCRIPTS = Path(".apm/skills/professor-contact/scripts")
NAMES = ["cmd_stage5_plan", "cmd_stage5_finalize", "stage5_recipient_authority",
         "cmd_stage5_rebuild_overview", "cmd_stage5_record_validation"]
EXPECTED_PARAMS = set("""atomic_write atomic_json emit fail soft_exit contact_evidence_decisions
resolve_contact_evidence SCHEMA MANAGED_BY EMAIL_PACK EMAIL_STATE EMAIL_OVERVIEW STAGE5_AUDIT_PROVENANCE
VERIFY_TIMESTAMP_FORMAT now_utc sha256_bytes sha256_text sha256_obj read_json_file
require_professor_dir_under_program truncate rel_path render_frontmatter split_frontmatter load_profile_text
load_header_sources header_values subject_line current_source_fingerprints verify_state gap_job_block
stage5_output_peers stage5_output_paths stage5_output_id stage5_mode stage5_pack_owner stage5_local_pack
stage5_choices_by_id validate_email_raw require_user_choices require_followup_choices
find_followup_template_path load_id_map humanized_paths assemble_draft assemble_followup_draft
body_salutation_line render_checklist_table render_source_table render_followup_source_table
render_fact_check_card""".split())

runner_src = (SCRIPTS / "contact_state.py").read_text()
runner = ast.parse(runner_src)
module = ast.parse((SCRIPTS / "_stage5_commands.py").read_text())

build = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == "build")
args = {a.arg for a in build.args.kwonlyargs}
assert args == EXPECTED_PARAMS, (len(args), sorted(EXPECTED_PARAMS - args), sorted(args - EXPECTED_PARAMS))
assert not build.args.args and not build.args.posonlyargs and not build.args.vararg and not build.args.kwarg
assert all(d is None for d in build.args.kw_defaults), build.args.kw_defaults
returned = next(n for n in ast.walk(build) if isinstance(n, ast.Return)
                and isinstance(n.value, ast.Call) and ast.unparse(n.value.func).endswith("SimpleNamespace"))
members = [k.arg for k in returned.value.keywords]
assert len(members) == 5 and set(members) == set(NAMES), members
print("T0 build takes exactly the 51 keyword-only parameters and returns 5 members OK")

aliases = [n for n in runner.body if isinstance(n, ast.Assign)
           and isinstance(n.targets[0], ast.Name)
           and ast.unparse(n.value).startswith("_stage5_commands.")]
assert len(aliases) == 5 and {n.targets[0].id for n in aliases} == set(NAMES)
assert all(ast.unparse(n.value) == "_stage5_commands." + n.targets[0].id for n in aliases)
print("T0 runner has the 5 same-name _stage5_commands aliases OK")

call = next(n for n in runner.body if isinstance(n, ast.Assign)
            and ast.unparse(n.targets[0]) == "_stage5_commands" and isinstance(n.value, ast.Call))
assert sorted(k.arg for k in call.value.keywords) == sorted(EXPECTED_PARAMS)
assert all(ast.unparse(k.value) == k.arg for k in call.value.keywords)
anchor = next(n for n in runner.body if isinstance(n, ast.FunctionDef) and n.name == "render_fact_check_card")
assert call.lineno > anchor.end_lineno, (anchor.end_lineno, call.lineno)
assert all(a.lineno > call.end_lineno for a in aliases)
print("T0 binding and all 5 aliases sit after render_fact_check_card OK")

assert 'Path(__file__).with_name("_stage5_commands.py")' in runner_src
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
运行该块时重定向到 `bash blk0.sh > /tmp/pc-stage13/t0.log 2>&1`。
预期：脚本 5 条 `T0 ... OK` + 1 条 `T0 CHECKS PASS`（日志首行还会打印 Python 版本）。

2. T1–T3（对照基准、`--help`、A/B；随后 docstring）：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage5-commands
RUN=/tmp/pc-stage13
rm -rf "$RUN/base"
mkdir -p "$RUN/base"
BASE_SHA=$(git rev-parse origin/refactor-stage5-input)
git archive "$BASE_SHA" .apm/skills/professor-contact/scripts | tar -x -C "$RUN/base"
uv run --no-project python "$RUN/base/.apm/skills/professor-contact/scripts/contact_state.py" --help >"$RUN/help-base.txt"
diff -u "$RUN/help-base.txt" "$RUN/help-head.txt"
wc -l /tmp/pc-stage2-tools/compare_stage2_batch_v2.py
shasum -a 256 /tmp/pc-stage2-tools/compare_stage2_batch_v2.py
uv run --no-project /tmp/pc-stage2-tools/compare_stage2_batch_v2.py \
  "$RUN/base/.apm/skills/professor-contact/scripts" \
  .apm/skills/professor-contact/scripts \
  _stage5_commands _stage5_commands \
  cmd_stage5_plan cmd_stage5_finalize stage5_recipient_authority \
  cmd_stage5_rebuild_overview cmd_stage5_record_validation >"$RUN/compare.log" 2>&1
cat "$RUN/compare.log"
```
预期：`diff` 无输出；**33 条 `OK`**（T0 3、T1 11、T2 8、T3 11）、`ALL CHECKS PASS`。输出落 `$RUN/compare.log`。

   随后 docstring 核对（依赖上一段导出的 `$RUN/base`；单独执行要先跑第 2 步上半段）：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage5-commands
RUN=/tmp/pc-stage13
wc -l /tmp/pc-stage2-tools/check_docstrings_v3.py
shasum -a 256 /tmp/pc-stage2-tools/check_docstrings_v3.py
uv run --no-project /tmp/pc-stage2-tools/check_docstrings_v3.py \
  "$RUN/base/.apm/skills/professor-contact/scripts" \
  .apm/skills/professor-contact/scripts \
  contact_state.py _stage5_commands.py \
  cmd_stage5_plan cmd_stage5_finalize stage5_recipient_authority \
  cmd_stage5_rebuild_overview cmd_stage5_record_validation >"$RUN/docstring.log" 2>&1
cat "$RUN/docstring.log"
```
预期整行：`total=5 with_doc=2 multi=2 clean_equal=2 without_doc=3 missing=0 mismatched=0` 与 `DOCSTRING CHECKS PASS`。输出落 `$RUN/docstring.log`。

3. T4：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage5-commands/.apm/skills/professor-contact/tests
uv run --no-project python -m unittest \
  test_contact_state.TestStage5.test_stage5_full_flow_and_fact_card \
  test_contact_state.TestStage5.test_stage5_both_outputs_followup_reuses_facts_and_date \
  test_contact_state.TestStage5.test_stage5_multiple_emails_use_distinct_files \
  test_contact_state.TestStage5.test_stage5_batch_failure_does_not_write_first_email \
  test_contact_state.TestStage5.test_humanizer_lost_title_rejected \
  test_contact_state.TestStage5.test_stage5_checklist_header_row_matches_body_salutation \
  test_contact_state.TestStage5.test_stage5_finalize_gate_stops_before_the_choices_file_is_read \
  test_contact_state.TestStage5.test_stage5_requires_user_template \
  test_contact_state.TestStage5.test_stage5_choices_id_mapping_fails_closed \
  test_contact_state.TestStage5TargetedEmailScope.test_issue59_t59_5_batch_mode_still_validates_every_pack_row \
  -v > /tmp/pc-stage13/t4.log 2>&1
cat /tmp/pc-stage13/t4.log
```
预期：`Ran 10 tests`、全部 `ok`；失败时先另存日志再重跑。

4. T5：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage5-commands/.apm/skills/professor-contact/tests
uv run --no-project python -m unittest \
  test_stage5_immutable.TestWrapperKeepsInstalledLayoutLocator.test_finalize_through_wrapper_certifies_installed_layout_checker \
  test_stage5_dualtarget_contract.InstalledSharedSkillsLocatorTests.test_installed_shared_skills_layout_locator_finds_sibling \
  -v > /tmp/pc-stage13/t5.log 2>&1
cat /tmp/pc-stage13/t5.log
```
预期：`Ran 2 tests`、全部 `ok`。

5. 失败处理：只在父提交上对照**同一个失败方法**，日志写进按 SHA 建的目录、按方法短名 + 时间戳命名；`METHOD` 默认值只是示例，实际要替换成真正失败的方法。
```sh
set -e
METHOD="${METHOD:-test_contact_state.TestStage5.test_stage5_full_flow_and_fact_card}"
BASE_SHA=$(git -C /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage5-commands rev-parse origin/refactor-stage5-input)
BASELINE=/tmp/pc-stage13/base-${BASE_SHA:0:12}
LOGDIR=/tmp/pc-stage13/logs/base-${BASE_SHA:0:12}
mkdir -p "$LOGDIR"
LOG="$LOGDIR/baseline-${METHOD##*.}-$(date +%Y%m%d-%H%M%S).log"
if [ ! -f "$BASELINE/.apm/skills/professor-contact/tests/${METHOD%%.*}.py" ]; then
  rm -rf "$BASELINE"
  mkdir -p "$BASELINE"
  git -C /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage5-commands archive "$BASE_SHA" | tar -x -C "$BASELINE"
fi
cd "$BASELINE/.apm/skills/professor-contact/tests"
uv run --no-project python -m unittest "$METHOD" -v >"$LOG" 2>&1 || true
cat "$LOG"
```
判据：父提交同一个方法也失败＝既有失败；父提交通过而工作树失败＝本批回归。日志名带方法短名与时间戳；没有失败时不执行本步。

6. 失败注入：本批不适用。本批只把定义搬到同目录模块并保持函数体逐字不变，不改事务、回滚、写入顺序、错误通道或 CLI 参数。

7. 既有仓库检查：PR 推送后引用 CI 运行编号，不作为通过条件。

## 不纳入本清单的范围

| 未纳入项 | 原因 |
| --- | --- |
| `validate_email_raw`／`assemble_draft`／`render_*` 等 19 个 helper | 后续批次 |
| Stage 4、迁移、剩余共享 helper | 后续批次 |
| 全量套件的本地重跑 | 仓库 CI 已分片执行 |
| R6 的空行接缝 | 属实现侧核对 |

## 修订记录

- 第 1 版：首次提交（含演练实测的 33 条 OK、10＋2 个方法与 docstring 期望值）。
- 第 2 版：按第一关意见修正——T4 换掉 4 个只执行 Stage 3 命令的方法，改为 1 个 finalize 门禁、2 个 plan 校验与 1 个 batch 模式方法（仍 10 个）；补四条命令的覆盖分布；helper 计数改为 19；T2 限定为函数/类定义；T0 的 from-import 禁用名加 `path`／`modules`；失败处理的目录 guard 改查方法所在文件、日志移入 `logs/` 子目录。
- 第 3 版：按第一关复核修正——第 3 步命令换成新 4 个方法并用更新后的命令重跑；日志目录移到 `$BASELINE` 之外；版本指针改计划第 3 版。

## 审核状态

- 第 1 版：第一关 NEEDS_MODIFICATION（T4 有 4 个方法不经过本批代码）。
- 第 2 版：第一关 NEEDS_MODIFICATION（命令未随表格更新、日志会被 `rm -rf` 删掉）。
- 第 3 版：第 3 步命令替换为新 4 个方法并用更新后的命令重跑（`Ran 10 tests in 5.773s`、`OK`）；日志目录移到 `$BASELINE` 之外（`/tmp/pc-stage13/logs/base-<sha12>`）；版本指针改计划第 3 版。第一关 PASS。
