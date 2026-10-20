# Stage 5 划分第三批：邮件组装与渲染（测试计划）

## 版本、来源与状态

- 对应执行计划：[implementation-plan.md](implementation-plan.md)，计划第 1 版（待审核）。
- Target repository revision: 工作分支 `refactor-stage5-helpers`；对照基准为父分支 `refactor-migrate`（#123）的 head，命令里用 `git rev-parse` 动态取（当前 `4a1138a`）。
- Test plan revision: 第 2 版。
- 测试范围依据：`Test Engineer Rule.md`。

## 必测清单

| 编号 | 业务目标 | 输入 / 场景 | 预期结果 | 检查方式 |
| --- | --- | --- | --- | --- |
| T0 | 模块可编译、可加载，工厂契约与别名顺序正确（R1、R3、R4） | 工作树 `scripts/contact_state.py`、`scripts/_stage5_email.py` | `py_compile` 成功；`--help` 退出码 0；`build()` 参数精确等于 14 个名字、无位置参数无默认值；返回 22 个成员；22 个同名别名；绑定调用与别名都晚于 `DEFAULT_ALMA_MATER`、且早于 `_stage5_commands` 的 `build()`；模块不导入 runner、无动态加载、不碰 `sys.path`／`sys.modules`；22 个名字不再在 runner 顶层定义（本步只查 `FunctionDef`；`AsyncFunctionDef`／`ClassDef` 由第 2 步的 T1 覆盖） | 第 1 步命令；5 条 `T0 ... OK` + 1 条 `T0 CHECKS PASS` |
| T1 | 22 个定义确实离开 runner 顶层（R1） | 对照基准与工作树 | base 仍定义 22 个、head 一个都不定义；模块存在；逐个“runner 已无 / 模块 `build()` 内有” | 第 2 步脚本的 `T0`／`T1` 行，共 48 条 `OK` |
| T2 | 搬移没有改变逻辑（R2） | 两侧源码 | 22 个定义的 AST 相同（比较时忽略 docstring）；docstring 5 个有（2 个多行）清洗后同文、17 个原本没有；runner 其余函数/类定义不变；离开的是这 22 个；22 个都有别名 | 同一脚本的 `T2` 行（25 条 `OK`）+ docstring 段 |
| T3 | 旧接口与加载方式不变（R3、R4、R5） | 两侧 runner | 22 个名字都可调用、签名相同；`--help` 逐字节相同；用 `Path(__file__).with_name("_stage5_email.py")` 加载；14 个实参同名同集合、22 个别名在调用之后 | 同一脚本的 `T3` 行（45 条 `OK`：44 条 callable／签名 + 1 条 `--help` 直接执行）；14 个实参、22 个别名顺序与 `Path(__file__).with_name` 加载由第 1 步 T0 脚本核对；`--help` 字节相同由第 2 步 `diff -u` 核对；合计 **118 条 `OK`**、`ALL CHECKS PASS` |
| T4 | 邮件组装、渲染与用户选择校验的行为不变（R2） | 10 个既有方法（均经真实 CLI 子进程）：`test_contact_state.TestStage5` 的 9 个（`test_stage5_full_flow_and_fact_card`、`test_stage5_both_outputs_followup_reuses_facts_and_date`、`test_stage5_multiple_emails_use_distinct_files`、`test_stage5_batch_failure_does_not_write_first_email`、`test_humanizer_lost_title_rejected`、`test_stage5_checklist_header_row_matches_body_salutation`、`test_stage5_choices_cannot_replace_the_verified_recipient`、`test_stage5_first_allows_missing_initial_sent_date`、`test_stage5_requires_explicit_user_choices`）；`test_contact_state.TestStage5TargetedEmailScope.test_issue59_t59_5_batch_mode_still_validates_every_pack_row` | **条件式通过条件**：10 个方法全部 `ok` 则通过；有失败时按第 5 步只对照**同一个失败方法**。注意这些方法覆盖 plan 与 finalize 两条路径（`first_allows_missing_initial_sent_date` 只走 plan、`choices_cannot_replace` 走 plan 与 finalize）；其中 `full_flow`／`both_outputs` 还驱动 `stage5-record-validation`、`multiple`／`issue59_t59_5` 还驱动 `stage5-rebuild-overview`、`choices_cannot_replace` 涉及收件人权限，这些属跨批依赖——失败时按第 5 步单方法归因，不直接算本批回归 | 第 3 步命令；`Ran 10 tests`、`OK`。输出落 `/tmp/pc-stage16/t4.log` |
| T5 | 复制 runner 的既有夹具仍能加载新模块（R1、R5） | `test_stage5_immutable.TestWrapperKeepsInstalledLayoutLocator.test_finalize_through_wrapper_certifies_installed_layout_checker`、`test_stage5_dualtarget_contract.InstalledSharedSkillsLocatorTests.test_installed_shared_skills_layout_locator_finds_sibling` | 两方法 `OK` 只证明复制布局含 `_stage5_email.py` 并成功加载；方法内的业务断言（wrapper finalize、contact evidence）属 Stage 5，失败时按第 5 步单方法对照 | 第 4 步命令；`Ran 2 tests`、`OK`。输出落 `/tmp/pc-stage16/t5.log` |

**既有仓库检查（不属于本批业务必测清单）**：仓库 CI 的 4 个 `shards` 与聚合 job `test` 照常执行，不作为通过条件。

## 执行步骤

1. T0（编译、工厂契约、别名顺序、模块源码约束）：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage5-helpers
RUN=/tmp/pc-stage16
mkdir -p "$RUN"
uv run --no-project python --version
uv run --no-project python -m py_compile \
  .apm/skills/professor-contact/scripts/contact_state.py \
  .apm/skills/professor-contact/scripts/_stage5_email.py
uv run --no-project python .apm/skills/professor-contact/scripts/contact_state.py --help >"$RUN/help-head.txt"
uv run --no-project python - <<'PY'
import ast
from pathlib import Path

SCRIPTS = Path(".apm/skills/professor-contact/scripts")
NAMES = ["email_source_hash", "find_boshu_analysis", "load_header_sources", "header_values",
         "subject_line", "compact_name", "email_item_is_evidence_seeded", "current_source_fingerprints",
         "validate_email_raw", "require_user_choices", "require_followup_choices",
         "find_followup_template_path", "load_id_map", "humanized_paths", "email_template_body",
         "assemble_draft", "body_salutation_line", "render_checklist_table", "cell_source",
         "render_source_table", "render_followup_source_table", "render_fact_check_card"]
EXPECTED_PARAMS = set("""EMAIL_SOURCE_HASH_FIELDS sha256_obj read_json_file BATCH_RE CLOSING_RE
INTEREST_HARD_CAP INTEREST_SOFT_CAP fail stage5_mode stage5_output_id DEFAULT_ALMA_MATER EMAIL_PACK
now_utc rel_path""".split())

runner_src = (SCRIPTS / "contact_state.py").read_text()
runner = ast.parse(runner_src)
module = ast.parse((SCRIPTS / "_stage5_email.py").read_text())

build = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == "build")
args = {a.arg for a in build.args.kwonlyargs}
assert args == EXPECTED_PARAMS, (len(args), sorted(EXPECTED_PARAMS - args), sorted(args - EXPECTED_PARAMS))
assert not build.args.args and not build.args.posonlyargs and not build.args.vararg and not build.args.kwarg
assert all(d is None for d in build.args.kw_defaults), build.args.kw_defaults
returned = next(n for n in ast.walk(build) if isinstance(n, ast.Return)
                and isinstance(n.value, ast.Call) and ast.unparse(n.value.func).endswith("SimpleNamespace"))
members = [k.arg for k in returned.value.keywords]
assert len(members) == 22 and set(members) == set(NAMES), (len(members), sorted(set(NAMES) ^ set(members)))
print("T0 build takes exactly the 14 keyword-only parameters and returns 22 members OK")

aliases = [n for n in runner.body if isinstance(n, ast.Assign)
           and isinstance(n.targets[0], ast.Name)
           and ast.unparse(n.value).startswith("_stage5_email.")]
assert len(aliases) == 22 and {n.targets[0].id for n in aliases} == set(NAMES)
assert all(ast.unparse(n.value) == "_stage5_email." + n.targets[0].id for n in aliases)
print("T0 runner has the 22 same-name _stage5_email aliases OK")

call = next(n for n in runner.body if isinstance(n, ast.Assign)
            and ast.unparse(n.targets[0]) == "_stage5_email" and isinstance(n.value, ast.Call))
assert sorted(k.arg for k in call.value.keywords) == sorted(EXPECTED_PARAMS)
assert all(ast.unparse(k.value) == k.arg for k in call.value.keywords)
alma = next(n for n in runner.body if isinstance(n, ast.Assign)
            and any(getattr(t, "id", "") == "DEFAULT_ALMA_MATER" for t in n.targets))
commands_build = next(n for n in runner.body if isinstance(n, ast.Assign)
                      and ast.unparse(n.targets[0]) == "_stage5_commands" and isinstance(n.value, ast.Call))
assert alma.lineno < call.lineno < commands_build.lineno, (alma.lineno, call.lineno, commands_build.lineno)
assert all(a.lineno > call.end_lineno for a in aliases)
assert all(a.lineno < commands_build.lineno for a in aliases)
print("T0 binding and all 22 aliases sit between DEFAULT_ALMA_MATER and the commands factory OK")

assert 'Path(__file__).with_name("_stage5_email.py")' in runner_src
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
print("T0 none of the 22 names is defined at runner top level OK")
print("T0 CHECKS PASS")
PY
```
运行该块时重定向到 `bash blk0.sh > /tmp/pc-stage16/t0.log 2>&1`。
预期：脚本 5 条 `T0 ... OK` + 1 条 `T0 CHECKS PASS`。

2. T1–T3（对照基准、`--help`、A/B；随后 docstring）：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage5-helpers
RUN=/tmp/pc-stage16
rm -rf "$RUN/base"
mkdir -p "$RUN/base"
BASE_SHA=$(git rev-parse origin/refactor-migrate)
git archive "$BASE_SHA" .apm/skills/professor-contact/scripts | tar -x -C "$RUN/base"
uv run --no-project python "$RUN/base/.apm/skills/professor-contact/scripts/contact_state.py" --help >"$RUN/help-base.txt"
diff -u "$RUN/help-base.txt" "$RUN/help-head.txt"
wc -l /tmp/pc-stage2-tools/compare_stage2_batch_v2.py
shasum -a 256 /tmp/pc-stage2-tools/compare_stage2_batch_v2.py
uv run --no-project /tmp/pc-stage2-tools/compare_stage2_batch_v2.py \
  "$RUN/base/.apm/skills/professor-contact/scripts" \
  .apm/skills/professor-contact/scripts \
  _stage5_email _stage5_email \
  email_source_hash find_boshu_analysis load_header_sources header_values subject_line compact_name \
  email_item_is_evidence_seeded current_source_fingerprints validate_email_raw require_user_choices \
  require_followup_choices find_followup_template_path load_id_map humanized_paths email_template_body \
  assemble_draft body_salutation_line render_checklist_table cell_source render_source_table \
  render_followup_source_table render_fact_check_card >"$RUN/compare.log" 2>&1
cat "$RUN/compare.log"
```
预期：`diff` 无输出；**118 条 `OK`**（T0 3、T1 45、T2 25、T3 45）、`ALL CHECKS PASS`。

   随后 docstring 核对（依赖上一段导出的 `$RUN/base`）：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage5-helpers
RUN=/tmp/pc-stage16
wc -l /tmp/pc-stage2-tools/check_docstrings_v3.py
shasum -a 256 /tmp/pc-stage2-tools/check_docstrings_v3.py
uv run --no-project /tmp/pc-stage2-tools/check_docstrings_v3.py \
  "$RUN/base/.apm/skills/professor-contact/scripts" \
  .apm/skills/professor-contact/scripts \
  contact_state.py _stage5_email.py \
  email_source_hash find_boshu_analysis load_header_sources header_values subject_line compact_name \
  email_item_is_evidence_seeded current_source_fingerprints validate_email_raw require_user_choices \
  require_followup_choices find_followup_template_path load_id_map humanized_paths email_template_body \
  assemble_draft body_salutation_line render_checklist_table cell_source render_source_table \
  render_followup_source_table render_fact_check_card >"$RUN/docstring.log" 2>&1
cat "$RUN/docstring.log"
```
预期整行：`total=22 with_doc=5 multi=2 clean_equal=5 without_doc=17 missing=0 mismatched=0` 与 `DOCSTRING CHECKS PASS`。

3. T4：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage5-helpers/.apm/skills/professor-contact/tests
uv run --no-project python -m unittest \
  test_contact_state.TestStage5.test_stage5_full_flow_and_fact_card \
  test_contact_state.TestStage5.test_stage5_both_outputs_followup_reuses_facts_and_date \
  test_contact_state.TestStage5.test_stage5_multiple_emails_use_distinct_files \
  test_contact_state.TestStage5.test_stage5_batch_failure_does_not_write_first_email \
  test_contact_state.TestStage5.test_humanizer_lost_title_rejected \
  test_contact_state.TestStage5.test_stage5_checklist_header_row_matches_body_salutation \
  test_contact_state.TestStage5.test_stage5_choices_cannot_replace_the_verified_recipient \
  test_contact_state.TestStage5.test_stage5_first_allows_missing_initial_sent_date \
  test_contact_state.TestStage5TargetedEmailScope.test_issue59_t59_5_batch_mode_still_validates_every_pack_row \
  test_contact_state.TestStage5.test_stage5_requires_explicit_user_choices \
  -v > /tmp/pc-stage16/t4.log 2>&1
cat /tmp/pc-stage16/t4.log
```
预期：`Ran 10 tests`、全部 `ok`；失败时保存日志后进入第 5 步单方法对照，不重复跑正式集合。

4. T5：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage5-helpers/.apm/skills/professor-contact/tests
uv run --no-project python -m unittest \
  test_stage5_immutable.TestWrapperKeepsInstalledLayoutLocator.test_finalize_through_wrapper_certifies_installed_layout_checker \
  test_stage5_dualtarget_contract.InstalledSharedSkillsLocatorTests.test_installed_shared_skills_layout_locator_finds_sibling \
  -v > /tmp/pc-stage16/t5.log 2>&1
cat /tmp/pc-stage16/t5.log
```
预期：`Ran 2 tests`、全部 `ok`。

5. 失败处理：只在父提交上对照**同一个失败方法**，日志放 `$BASELINE` 之外的 `logs/` 目录；`METHOD` 默认值只是示例，实际要替换成真正失败的方法。
```sh
set -e
METHOD="${METHOD:-test_contact_state.TestStage5.test_stage5_full_flow_and_fact_card}"
BASE_SHA=$(git -C /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage5-helpers rev-parse origin/refactor-migrate)
BASELINE=/tmp/pc-stage16/base-${BASE_SHA:0:12}
LOGDIR=/tmp/pc-stage16/logs/base-${BASE_SHA:0:12}
mkdir -p "$LOGDIR"
LOG="$LOGDIR/baseline-${METHOD##*.}-$(date +%Y%m%d-%H%M%S).log"
if [ ! -f "$BASELINE/.apm/skills/professor-contact/tests/${METHOD%%.*}.py" ]; then
  rm -rf "$BASELINE"
  mkdir -p "$BASELINE"
  git -C /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage5-helpers archive "$BASE_SHA" | tar -x -C "$BASELINE"
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
| `compile_email_entry`／`_selection_direction_ids`／`validate_papers_override`／`assemble_followup_draft` | 被更早的 build 消费，下一批处理 |
| 候选校验、`verify_state`、contact evidence、stage1、迁移 helper | 后续批次 |
| 全量套件的本地重跑 | 仓库 CI 已分片执行 |
| R6 的空行接缝 | 属实现侧核对 |

## 修订记录

- 第 1 版：首次提交（含演练实测的 118 条 OK、10＋2 个方法与 docstring 期望值）。
- 第 2 版：按第一关意见修正——T4 换掉 3 个提前结束的方法（template_error／choices 装载／verify 门禁），改为 `choices_cannot_replace`（plan+finalize）、`first_allows_missing_initial_sent_date`（plan 组装）、`issue59_t59_5`（plan 产出 drafts），目标改为“邮件组装、渲染与用户选择校验”；T0 补“22 个别名都早于 `_stage5_commands` 的 build”断言；T3 的检查方式补引用第 1 步 T0 脚本。

## 审核状态

- 第 1 版：第一关 NEEDS_MODIFICATION（T4 有 4 个方法提前结束、未到组装渲染）。
- 第 2 版：待第一关复核。
