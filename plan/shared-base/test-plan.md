# 共享基础层划分第一批：哈希／时间／文本／方向身份／托管文件（测试计划）

## 版本、来源与状态

- 对应执行计划：[implementation-plan.md](implementation-plan.md)，计划第 1 版（待审核）。
- Requirement revision: 第 1 版（2026-10-20 负责人要求）。
- Target repository revision: 工作分支 `refactor-shared-base`；对照基准为分支链末位 `refactor-stage2-render`（#114）的 head `13efd40441a2bf8683c9da630bdc747248fc8c29`（GitHub 自动 rebase 前的同一提交是 `cf979ab`，两者 `scripts` 子树字节相同）。
- Test plan revision: 第 5 版。
- Proposed review status: 待审核。
- 测试范围依据：`Test Engineer Rule.md`。

## 必测清单

| 编号 | 业务目标 | 输入 / 场景 | 预期结果 | 检查方式 |
| --- | --- | --- | --- | --- |
| T0 | 模块可编译、可加载，工厂契约与别名顺序正确（R1、R3、R4） | 工作树 `scripts/contact_state.py`、`scripts/_contact_base.py` | 两个文件 `py_compile` 成功；`--help` 退出码 0；`build()` 的 keyword-only 参数**精确等于** 7 个名字集合、无位置参数；返回 40 个成员且去重后仍 40；runner 有 40 个 `X = _contact_base.X` 别名、无重名；绑定调用与 40 个别名都在 `_stage2_facts_module.build` 调用之前（`save_projections` 本身已搬走，无法再用它做锚点）；模块不导入 runner、不做动态加载、不碰 `sys.path`／`sys.modules` | 第 1 步命令；5 条 `T0 ... OK` 与 1 条 `T0 CHECKS PASS`（共 6 行） |
| T1 | 40 个定义确实离开 runner 顶层、进入模块 `build()`（R1） | 对照基准（`git archive 13efd40` 取出的 `scripts`）与工作树 `scripts` | `T0`：base 与 head 是两个不同目录、base 仍定义 40 个定义、head 一个都不定义；`T1`：模块存在；40 个定义逐个“runner 顶层已无 / 模块 `build()` 内有” | 第 2 步对比脚本的 `T0 ...`／`T1 ...` 行，共 84 条 `OK` |
| T2 | 搬移没有改变任何逻辑（R2） | 同上两侧源码 | 40 个定义的代码 AST 与基准完全相同（脚本忽略 docstring）；docstring 单独核对：清洗后与基准同文；runner 其余顶层定义 AST 不变；离开 runner 的定义正好是这 40 个、没有新增；40 个定义在 runner 都有别名 | 同一脚本的 `T2 ...` 行（43 条 `OK`）；docstring 用第 2 步的只读核对块 |
| T3 | 旧接口与加载方式不变（R3、R4、R5） | 同一进程内分别按文件路径加载两侧 runner；再以子进程直接执行改动后的 runner | 40 个名字在两侧都可调用、`inspect.signature` 字符串相同；`--help` 退出码 0 且与父提交逐字节相同；runner 用 `Path(__file__).with_name("_contact_base.py")` 加载；40 个实参与参数同名同集合、40 个别名都在调用之后 | 同一脚本的 `T3 ...` 行（81 条 `OK`）、第 1 步的源码约束核对、第 2 步的 `diff -u`；合计 208 条 `OK`、末尾 `ALL CHECKS PASS` |
| T4 | 哈希／文本／方向身份／托管写入的行为不变（R2） | 10 个既有方法（均为经真实 CLI 子进程或类内助手执行本批函数的路径；其中 6 个方法体内直接出现本批名字，4 个经助手间接引用 `cross_group_id`／`safe_result_file`／`quote_id` 或只做端到端断言；托管写入组经 `managed_write` 注入的 stage2 finalize 路径覆盖）：`test_contact_state.TestRunnerBasics.test_05e_overview_manual_edit_does_not_block_local_finalize`、`test_contact_state.Issue66RecordedValidationScopeTests.test_handoff_record_expands_global_blocker_to_rendered_objects`、`test_stage2_preflight.TestFinalizePreflightWiring.test_legacy_slow_path_seeds_metadata_for_next_run`、`test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_repeated_quote_locations_and_ambiguous_report`、`test_stage3_direction_groups.Stage3DirectionGroupTests.test_explicit_cross_group_generates_separate_job_and_section`、`test_stage3_direction_groups.Stage3DirectionGroupTests.test_participant_change_invalidates_only_cross_group`、`test_stage3_direction_identity.TestV2PackShape.test_facts_direction_id_survives_into_pack`、`test_stage3_direction_identity.TestV2PackShape.test_v1_pack_shared_paper_normalizes_to_one_record`、`test_stage2_facts_sidecar.FactsSidecarTests.test_invalid_facts_sidecar_shape_fails_closed`、`test_stage5_immutable.TestWrapperKeepsInstalledLayoutLocator.test_changed_audit_marker_fails_closed_before_writing_user_files` | **条件式通过条件**：10 个方法全部 `ok` 则 T4 通过；有失败时按第 5 步在父提交 `13efd40` 上跑同一组方法，基线同样失败记既有失败，基线通过而工作树失败记本批回归 | 第 3 步命令；`Ran 10 tests`、`OK`，无 skip／`FAIL`／`ERROR` |
| T5 | 复制 runner 的既有夹具仍能加载新模块（R1、R5） | `test_stage5_immutable.TestWrapperKeepsInstalledLayoutLocator.test_finalize_through_wrapper_certifies_installed_layout_checker`、`test_stage5_dualtarget_contract.InstalledSharedSkillsLocatorTests.test_installed_shared_skills_layout_locator_finds_sibling` | 复制布局包含 `_contact_base.py`，复制后的 runner 能按路径加载它；两方法 `OK` | 第 4 步命令；`Ran 2 tests`、`OK` |

**既有仓库检查（不属于本批业务必测清单）**：仓库 CI 的 4 个 `shards` 与聚合 job `test` 照常执行，结果按运行编号与 head 单独引用；本批不在本地重跑全量套件。

## 执行步骤

准备与执行都在工作树 `/Users/rekidunois/code/skill-repos-dev/worktrees/refactor-shared-base` 内进行；临时脚本与运行产物放仓库外 `/tmp/pc-stage8`。

1. T0：编译、工厂契约、别名顺序与模块源码约束（同一命令块，`set -e`）。该块放在 0 缩进，`<<'PY'` 的结束行可按原样执行。
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-shared-base
RUN=/tmp/pc-stage8
mkdir -p "$RUN"
uv run --no-project python --version
uv run --no-project python -m py_compile \
  .apm/skills/professor-contact/scripts/contact_state.py \
  .apm/skills/professor-contact/scripts/_contact_base.py
uv run --no-project python .apm/skills/professor-contact/scripts/contact_state.py --help >"$RUN/help-head.txt"
uv run --no-project python - <<'PY'
import ast
from pathlib import Path

SCRIPTS = Path(".apm/skills/professor-contact/scripts")
NAMES = [
    "now_utc", "sha256_bytes", "sha256_text", "sha256_obj", "normalized_quote", "quote_id",
    "load_json", "read_json_file", "professor_dir_containment_error",
    "require_professor_dir_under_program", "truncate", "text_tokens", "title_tokens", "rel_path",
    "filename_component", "safe_result_file", "direction_machine_id", "facts_direction_id",
    "cross_group_id", "pack_paper_index", "direction_papers", "paper_digest", "sidecar_sha",
    "gap_fingerprint", "candidate_fingerprint", "direction_relevant_keys",
    "direction_provisional_member_keys", "pack_direction_relevant_keys", "direction_candidate_keys",
    "selected_candidate_union", "direction_fingerprint", "render_frontmatter", "split_frontmatter",
    "managed_conflict", "managed_write", "managed_write_raw", "projection_conflict",
    "projection_write", "load_projections", "save_projections",
]
EXPECTED_PARAMS = {"atomic_write", "atomic_json", "fail", "MANAGED_BY",
                   "DIRECTION_IDENTITY_VERSION", "PROJECTIONS_FILE", "VERIFY_TIMESTAMP_FORMAT"}

runner_src = (SCRIPTS / "contact_state.py").read_text()
runner = ast.parse(runner_src)
module = ast.parse((SCRIPTS / "_contact_base.py").read_text())

def namespace_of(tree, builder="build"):
    build = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == builder)
    returned = next(n for n in ast.walk(build)
                    if isinstance(n, ast.Return) and isinstance(n.value, ast.Call)
                    and ast.unparse(n.value.func).endswith("SimpleNamespace"))
    return build, [k.arg for k in returned.value.keywords]

build, members = namespace_of(module)
args = {a.arg for a in build.args.kwonlyargs}
assert args == EXPECTED_PARAMS, (sorted(args), sorted(EXPECTED_PARAMS - args), sorted(args - EXPECTED_PARAMS))
assert not build.args.args and not build.args.vararg and not build.args.kwarg
assert len(members) == 40 and len(set(members)) == 40, len(members)
assert set(members) == set(NAMES), sorted(set(NAMES) ^ set(members))
print("T0 build takes exactly the 7 keyword-only parameters and returns 40 members OK")

aliases = [n for n in runner.body if isinstance(n, ast.Assign)
           and isinstance(n.targets[0], ast.Name)
           and ast.unparse(n.value).startswith("_contact_base.")]
assert len(aliases) == 40, len(aliases)
assert len({n.targets[0].id for n in aliases}) == 40
assert all(ast.unparse(n.value) == "_contact_base." + n.targets[0].id for n in aliases)
assert {n.targets[0].id for n in aliases} == set(NAMES)
print("T0 runner has 40 same-name _contact_base aliases OK")

call = next(n for n in runner.body if isinstance(n, ast.Assign)
            and ast.unparse(n.targets[0]) == "_contact_base"
            and isinstance(n.value, ast.Call))
assert sorted(k.arg for k in call.value.keywords) == sorted(EXPECTED_PARAMS)
facts_call = next(n for n in runner.body if isinstance(n, ast.Assign)
                  and ast.unparse(n.targets[0]) == "_stage2_facts" and isinstance(n.value, ast.Call))
assert call.lineno < facts_call.lineno, (call.lineno, facts_call.lineno)
assert all(a.lineno > call.end_lineno for a in aliases)
assert all(a.lineno < facts_call.lineno for a in aliases)
print("T0 binding and all 40 aliases precede the facts factory OK")

assert 'Path(__file__).with_name("_contact_base.py")' in runner_src
imported = {a.name for n in module.body if isinstance(n, ast.Import) for a in n.names}
imported |= {n.module or "" for n in module.body if isinstance(n, ast.ImportFrom)}
assert not any("contact_state" in name for name in imported), sorted(imported)
dotted = {ast.unparse(n) for n in ast.walk(module) if isinstance(n, ast.Attribute)}
assert not (dotted & {"sys.path", "sys.modules"}), sorted(dotted & {"sys.path", "sys.modules"})
dynamic = {"spec_from_file_location", "module_from_spec", "exec_module", "import_module"}
assert not {d for d in dotted if d.split(".")[-1] in dynamic}, sorted(dotted)
names_used = {n.id for n in ast.walk(module) if isinstance(n, ast.Name)}
assert not (names_used & {"__import__", "exec", "eval"}), sorted(names_used & {"__import__", "exec", "eval"})
print("T0 runner loads it by path, and the module has no runner import and no dynamic-import names OK")

builds = [n.lineno for n in runner.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in NAMES]
assert builds == [], builds
print("T0 none of the 40 names is defined at runner top level OK")
print("T0 CHECKS PASS")
PY
```
预期：`py_compile` 与 `--help` 无输出、退出码 0；脚本打印 5 条 `T0 ... OK` 与 1 条 `T0 CHECKS PASS`（共 6 行）。

2. T1–T3：取出对照基准、比对 `--help`、运行对比脚本与 docstring 核对：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-shared-base
RUN=/tmp/pc-stage8
mkdir -p "$RUN/base"
git archive 13efd40441a2bf8683c9da630bdc747248fc8c29 .apm/skills/professor-contact/scripts | tar -x -C "$RUN/base"
uv run --no-project python "$RUN/base/.apm/skills/professor-contact/scripts/contact_state.py" --help >"$RUN/help-base.txt"
diff -u "$RUN/help-base.txt" "$RUN/help-head.txt"
shasum -a 256 /tmp/pc-stage2-tools/compare_stage2_batch_v2.py
uv run --no-project /tmp/pc-stage2-tools/compare_stage2_batch_v2.py \
  "$RUN/base/.apm/skills/professor-contact/scripts" \
  .apm/skills/professor-contact/scripts \
  _contact_base _contact_base \
  now_utc sha256_bytes sha256_text sha256_obj normalized_quote quote_id load_json read_json_file \
  professor_dir_containment_error require_professor_dir_under_program truncate text_tokens \
  title_tokens rel_path filename_component safe_result_file direction_machine_id facts_direction_id \
  cross_group_id pack_paper_index direction_papers paper_digest sidecar_sha gap_fingerprint \
  candidate_fingerprint direction_relevant_keys direction_provisional_member_keys \
  pack_direction_relevant_keys direction_candidate_keys selected_candidate_union \
  direction_fingerprint render_frontmatter split_frontmatter managed_conflict managed_write \
  managed_write_raw projection_conflict projection_write load_projections save_projections
```
脚本来源 `/tmp/pc-stage2-tools/compare_stage2_batch_v2.py`，94 行，sha256 `1ba8c0f49346b1fa78c34fbeec4d82cdab206ebef6cbf1b629769f9e5e4346b6`；缺失或哈希不同时停止。
预期：`diff` 无输出；208 条 `OK`（`T0` 3、`T1` 81、`T2` 43、`T3` 81），末尾 `ALL CHECKS PASS`，退出码 0。

   随后做 docstring 核对（同一份两侧源码，只读）：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-shared-base
shasum -a 256 /tmp/pc-stage2-tools/check_docstrings_v3.py
uv run --no-project /tmp/pc-stage2-tools/check_docstrings_v3.py \
  /tmp/pc-stage8/base/.apm/skills/professor-contact/scripts \
  .apm/skills/professor-contact/scripts \
  contact_state.py _contact_base.py \
  now_utc sha256_bytes sha256_text sha256_obj normalized_quote quote_id load_json read_json_file \
  professor_dir_containment_error require_professor_dir_under_program truncate text_tokens \
  title_tokens rel_path filename_component safe_result_file direction_machine_id facts_direction_id \
  cross_group_id pack_paper_index direction_papers paper_digest sidecar_sha gap_fingerprint \
  candidate_fingerprint direction_relevant_keys direction_provisional_member_keys \
  pack_direction_relevant_keys direction_candidate_keys selected_candidate_union \
  direction_fingerprint render_frontmatter split_frontmatter managed_conflict managed_write \
  managed_write_raw projection_conflict projection_write load_projections save_projections
```
脚本 `/tmp/pc-stage2-tools/check_docstrings_v3.py`，109 行，sha256 `31c8b2081c5d1f5398d197d2992084f371d978d99084207a7a9e7f2880f29d4a`。
预期：`total=40 with_doc=13 multi=9 clean_equal=13 without_doc=27 missing=0 mismatched=0` 与 `DOCSTRING CHECKS PASS`，退出码 0。

3. T4：只跑清单列出的 10 个方法：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-shared-base/.apm/skills/professor-contact/tests
uv run --no-project python -m unittest \
  test_contact_state.TestRunnerBasics.test_05e_overview_manual_edit_does_not_block_local_finalize \
  test_contact_state.Issue66RecordedValidationScopeTests.test_handoff_record_expands_global_blocker_to_rendered_objects \
  test_stage2_preflight.TestFinalizePreflightWiring.test_legacy_slow_path_seeds_metadata_for_next_run \
  test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_repeated_quote_locations_and_ambiguous_report \
  test_stage3_direction_groups.Stage3DirectionGroupTests.test_explicit_cross_group_generates_separate_job_and_section \
  test_stage3_direction_groups.Stage3DirectionGroupTests.test_participant_change_invalidates_only_cross_group \
  test_stage3_direction_identity.TestV2PackShape.test_facts_direction_id_survives_into_pack \
  test_stage3_direction_identity.TestV2PackShape.test_v1_pack_shared_paper_normalizes_to_one_record \
  test_stage2_facts_sidecar.FactsSidecarTests.test_invalid_facts_sidecar_shape_fails_closed \
  test_stage5_immutable.TestWrapperKeepsInstalledLayoutLocator.test_changed_audit_marker_fails_closed_before_writing_user_files \
  -v
```
预期：`Ran 10 tests`、全部 `ok`；无 `skipped`／`FAIL`／`ERROR`。

4. T5：只跑清单列出的 2 个夹具方法：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-shared-base/.apm/skills/professor-contact/tests
uv run --no-project python -m unittest \
  test_stage5_immutable.TestWrapperKeepsInstalledLayoutLocator.test_finalize_through_wrapper_certifies_installed_layout_checker \
  test_stage5_dualtarget_contract.InstalledSharedSkillsLocatorTests.test_installed_shared_skills_layout_locator_finds_sibling \
  -v
```
预期：`Ran 2 tests`、全部 `ok`。

5. 失败处理：T4／T5 有失败时（12 个方法一起跑），先按本批回归排查，在父提交 `13efd40` 上跑同一组方法：
```sh
set -e
BASELINE=/tmp/pc-stage8/base-parent
rm -rf "$BASELINE"
mkdir -p "$BASELINE"
git -C /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-shared-base archive 13efd40441a2bf8683c9da630bdc747248fc8c29 | tar -x -C "$BASELINE"
cd "$BASELINE/.apm/skills/professor-contact/tests"
uv run --no-project python -m unittest \
  test_contact_state.TestRunnerBasics.test_05e_overview_manual_edit_does_not_block_local_finalize \
  test_contact_state.Issue66RecordedValidationScopeTests.test_handoff_record_expands_global_blocker_to_rendered_objects \
  test_stage2_preflight.TestFinalizePreflightWiring.test_legacy_slow_path_seeds_metadata_for_next_run \
  test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_repeated_quote_locations_and_ambiguous_report \
  test_stage3_direction_groups.Stage3DirectionGroupTests.test_explicit_cross_group_generates_separate_job_and_section \
  test_stage3_direction_groups.Stage3DirectionGroupTests.test_participant_change_invalidates_only_cross_group \
  test_stage3_direction_identity.TestV2PackShape.test_facts_direction_id_survives_into_pack \
  test_stage3_direction_identity.TestV2PackShape.test_v1_pack_shared_paper_normalizes_to_one_record \
  test_stage2_facts_sidecar.FactsSidecarTests.test_invalid_facts_sidecar_shape_fails_closed \
  test_stage5_immutable.TestWrapperKeepsInstalledLayoutLocator.test_changed_audit_marker_fails_closed_before_writing_user_files \
  test_stage5_immutable.TestWrapperKeepsInstalledLayoutLocator.test_finalize_through_wrapper_certifies_installed_layout_checker \
  test_stage5_dualtarget_contract.InstalledSharedSkillsLocatorTests.test_installed_shared_skills_layout_locator_finds_sibling \
  -v > /tmp/pc-stage8/baseline.log 2>&1 || true
cat /tmp/pc-stage8/baseline.log
```
判据：基线同样失败＝既有失败；基线通过而工作树失败＝本批回归。

6. 失败注入：本批不适用。本批只搬移定义，不改事务、回滚、写入顺序或错误通道实现；`managed_write` 走的仍是同一套 `atomic_write`／`fail`，必测清单里没有失败注入项。

7. 既有仓库检查（不属于本批必测项，也不作为通过条件）：PR 推送后引用 4 个 `shards` 与聚合 job `test` 的运行编号与结论。

## 不纳入本清单的范围

| 未纳入项 | 原因 |
| --- | --- |
| 输入包规范化、候选状态、Stage 3／4／5 主体与迁移命令 | 属后续批次 |
| 全量套件的本地重跑 | 仓库 CI 已分片执行，不作为本批必测 |
| 新模块单独的可导入性单测 | T0 的直接执行、T3 的按路径加载与 T5 的两条复制加载路径已覆盖真实加载方式 |
| R6 的 diff 接缝与「常量值不变」 | R6 属实现侧 diff 核对（执行计划第 3–4 步）；常量值由 T4／T5 的真实 CLI 行为覆盖，不单列用例 |

## 修订记录

- 第 1 版：首次提交。
- 第 2 版：按演练实测写明 docstring 期望值（13 个有 docstring、其中 9 个多行、27 个原本没有）；其余判据与步骤不变。
- 第 3 版：按第一关意见改 T4 筛选依据的表述（6 个直接引用、4 个经助手间接引用，托管写入经 finalize 路径覆盖）与 T0 条数写法（5 条 OK + 1 条 PASS），并补 `__import__`／`exec`／`eval` 黑名单、别名早于首个消费方两条断言、T5 标注与 R6 归属说明。
- 第 4 版：修 T0 锚点——`save_projections` 已搬走，不再用它做位置判据，改为断言绑定调用与 40 个别名都早于 `_stage2_facts.build(...)`；print 文案同步。
- 第 5 版：按第一关复核补版本记录并确认内容——T4 行去掉 `／render`（托管写入经 stage2 finalize 路径覆盖）、T0 的 print 与断言一一对应（`__import__`／`exec`／`eval` 黑名单归到模块源码那条）、T0 重跑为 5 条 OK + 1 条 PASS。

## 审核状态

- 第 1 版：待审核。
- 第 2 版：第一关 NEEDS_MODIFICATION（K1 T4 筛选依据表述与事实不符；K2 T0 条数写法有歧义）。
- 第 3 版：第一关 NEEDS_MODIFICATION（K1／K2）；已改文字并补断言。
- 第 4 版：按复核实测修正 T0 脚本——`save_projections` 搬走后不再是 runner 顶层函数，锚点改为「绑定调用与 40 个别名都在 `_stage2_facts.build(...)` 之前」；用例集合与执行命令未变。
