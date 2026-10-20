# 共享基础层第二批：输入包规范化和候选状态（测试计划）

## 版本、来源与状态

- 对应执行计划：[implementation-plan.md](implementation-plan.md)，计划第 2 版。
- Requirement revision: 第 1 版（2026-10-20 负责人要求；同一系列见 PR #95–#116）。
- Target repository revision: 工作分支 `refactor-input-pack`；对照基准为父分支 `refactor-shared-base`（#116）的 head `4ff8ff6`。堆栈被自动 rebase 时按分支名重新取值（`git rev-parse origin/refactor-shared-base`），程序内容不变。
- Test plan revision: 第 3 版。
- Proposed review status: 待审核。
- 测试范围依据：`Test Engineer Rule.md`。

## 必测清单

| 编号 | 业务目标 | 输入 / 场景 | 预期结果 | 检查方式 |
| --- | --- | --- | --- | --- |
| T0 | 模块可编译、可加载，工厂契约与别名顺序正确（R1、R3、R4） | 工作树 `scripts/contact_state.py`、`scripts/_contact_pack.py` | 两文件 `py_compile` 成功；`--help` 退出码 0；`build()` 的 keyword-only 参数**精确等于** 14 个名字集合、无位置参数；返回 11 个成员且去重后仍 11；runner 有 11 个 `X = _contact_pack.X` 别名、集合与成员一致；绑定调用与 11 个别名都在 `_contact_base` 最后一个别名之后、`_stage2_facts_module.build` 之前；模块不导入 runner、无动态加载、不碰 `sys.path`／`sys.modules`；11 个名字不再在 runner 顶层定义 | 第 1 步命令；5 条 `T0 ... OK` + 1 条 `T0 CHECKS PASS`（共 6 行） |
| T1 | 11 个定义确实离开 runner 顶层、进入模块 `build()`（R1） | 对照基准（父分支 head 导出的 `scripts`）与工作树 `scripts` | `T0`：base 与 head 是两个不同目录、base 仍定义 11 个定义、head 一个都不定义；`T1`：模块存在；11 个定义逐个“runner 顶层已无 / 模块 `build()` 内有” | 第 2 步对比脚本的 `T0 ...`／`T1 ...` 行，共 26 条 `OK` |
| T2 | 搬移没有改变任何逻辑（R2） | 同上两侧源码 | 11 个定义的代码 AST 与基准完全相同（脚本忽略 docstring）；docstring 单独核对：10 个有 docstring（其中 9 个多行）清洗后同文、1 个原本没有；runner 其余顶层定义 AST 不变；离开 runner 的定义正好是这 11 个、没有新增；11 个名字都有别名 | 同一脚本的 `T2 ...` 行（14 条 `OK`）；docstring 用第 2 步第二段 |
| T3 | 旧接口与加载方式不变（R3、R4、R5） | 同一进程内分别按文件路径加载两侧 runner；再以子进程直接执行改动后的 runner | 11 个名字在两侧都可调用、`inspect.signature` 字符串相同；`--help` 退出码 0 且与父提交逐字节相同；runner 用 `Path(__file__).with_name("_contact_pack.py")` 加载；14 个实参与参数同名同集合、11 个别名都在调用之后 | 同一脚本的 `T3 ...` 行（23 条 `OK`）、第 1 步的源码约束核对、第 2 步的 `diff -u`；合计 **63 条 `OK`**、末尾 `ALL CHECKS PASS` |
| T4 | 输入包 v1 规范化、候选状态 v2 读取与 v1 候选状态迁移、严格形状（R2） | 10 个既有方法（2 个直接调用 `normalize_input_pack`；1 个是 stage2 输出契约；其余经命令路径走到本批定义）：`test_stage3_direction_identity.TestV2PackShape` 的 3 个（`test_pack_has_one_canonical_paper_record_per_item_key`、`test_v1_pack_with_conflicting_shared_paper_fails_closed`、`test_v1_pack_shared_paper_normalizes_to_one_record`；其中两个 `test_v1_pack_*` 方法体内直接调用 `normalize_input_pack`，`test_pack_has_one_*` 是 stage2 输出契约）；`test_stage3_direction_groups.Stage3DirectionGroupTests` 的 2 个（`test_stage4_exactly_migrates_v1_candidate_state_with_pack_mapping_without_stage3_rerun`、`test_stage4_same_professor_preserved_entry_needs_refresh_is_zero_write`）；`test_issue66_stage3_local_state.Issue66LocalStateTests.test_rebuild_overview_only_migrates_a_unique_legacy_identity`；`test_contact_state.Issue67ProfessorLocalStage4Tests.test_02_professor_own_invalid_state_input_or_selection_writes_nothing`；`test_build_issue29_stage2_fixture.BuildIssue29Stage2FixtureTests` 的 2 个（`test_reuse_all_builds_the_accepted_state_contract`、`test_single_paper_builds_a_fresh_single_candidate_root`）；`test_contact_state.TestRunnerBasics.test_05b_collection_key_limits_stage3` | **条件式通过条件**：10 个方法全部 `ok` 则 T4 通过；有失败时按第 5 步在父提交上只对照**同一个失败方法**，父提交同样失败记既有失败，父提交通过而工作树失败记本批回归 | 第 3 步命令；`Ran 10 tests`、`OK`，无 skip／`FAIL`／`ERROR`。**已知限制**：`_slice_gap_directions` 与 `_migrate_v1_cross_group` 只有 T2 的 AST 等价覆盖，没有既有行为测试（`grep -rn '"cross_direction":' tests` 为 0）；要补行为用例需要验收决定人批准新增测试，本批不扩范围 |
| T5 | 复制 runner 的既有夹具仍能加载新模块（R1、R5） | `test_stage5_immutable.TestWrapperKeepsInstalledLayoutLocator.test_finalize_through_wrapper_certifies_installed_layout_checker`、`test_stage5_dualtarget_contract.InstalledSharedSkillsLocatorTests.test_installed_shared_skills_layout_locator_finds_sibling` | 复制布局包含 `_contact_pack.py`，复制后的 runner 能按路径加载它；两方法 `OK` | 第 4 步命令；`Ran 2 tests`、`OK` |

**既有仓库检查（不属于本批业务必测清单）**：仓库 CI 的 4 个 `shards` 与聚合 job `test` 照常执行，结果按运行编号与 head 单独引用；本批不在本地重跑全量套件。

## 执行步骤

准备与执行都在工作树 `/Users/rekidunois/code/skill-repos-dev/worktrees/refactor-input-pack` 内进行；临时脚本与运行产物放仓库外 `/tmp/pc-stage9`。

1. T0：编译、工厂契约、别名顺序与模块源码约束（同一命令块，`set -e`）。该块放在 0 缩进，`<<'PY'` 的结束行可按原样执行。
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-input-pack
RUN=/tmp/pc-stage9
mkdir -p "$RUN"
uv run --no-project python --version
uv run --no-project python -m py_compile \
  .apm/skills/professor-contact/scripts/contact_state.py \
  .apm/skills/professor-contact/scripts/_contact_pack.py
uv run --no-project python .apm/skills/professor-contact/scripts/contact_state.py --help >"$RUN/help-head.txt"
uv run --no-project python - <<'PY'
import ast
from pathlib import Path

SCRIPTS = Path(".apm/skills/professor-contact/scripts")
NAMES = ["_canonical_paper_record", "_merge_canonical_paper", "normalize_input_pack",
         "load_input_pack", "_migrate_v1_candidate", "_slice_gap_directions",
         "_migrate_v1_cross_group", "normalize_candidate_state", "load_candidate_state",
         "_strict_candidate_shape", "strict_candidate_state"]
EXPECTED_PARAMS = {"fail", "soft_exit", "INPUT_PACK_SCHEMA", "CANDIDATE_STATE_SCHEMA",
                   "DIRECTION_IDENTITY_VERSION", "STAGE3_GENERATOR_CONTRACT_VERSION",
                   "INPUT_PACK_KIND", "CANDIDATE_STATE_KIND", "INPUT_PACK", "CANDIDATE_STATE",
                   "_CANONICAL_PAPER_FIELDS", "read_json_file", "direction_machine_id",
                   "cross_group_id"}

runner_src = (SCRIPTS / "contact_state.py").read_text()
runner = ast.parse(runner_src)
module = ast.parse((SCRIPTS / "_contact_pack.py").read_text())

build = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == "build")
args = {a.arg for a in build.args.kwonlyargs}
assert args == EXPECTED_PARAMS, (sorted(args), sorted(EXPECTED_PARAMS - args), sorted(args - EXPECTED_PARAMS))
assert not build.args.args and not build.args.vararg and not build.args.kwarg
returned = next(n for n in ast.walk(build) if isinstance(n, ast.Return)
                and isinstance(n.value, ast.Call) and ast.unparse(n.value.func).endswith("SimpleNamespace"))
members = [k.arg for k in returned.value.keywords]
assert len(members) == 11 and len(set(members)) == 11, members
assert set(members) == set(NAMES), sorted(set(NAMES) ^ set(members))
print("T0 build takes exactly the 14 keyword-only parameters and returns 11 members OK")

aliases = [n for n in runner.body if isinstance(n, ast.Assign)
           and isinstance(n.targets[0], ast.Name)
           and ast.unparse(n.value).startswith("_contact_pack.")]
assert len(aliases) == 11 and len({n.targets[0].id for n in aliases}) == 11
assert {n.targets[0].id for n in aliases} == set(NAMES)
assert all(ast.unparse(n.value) == "_contact_pack." + n.targets[0].id for n in aliases)
print("T0 runner has the 11 same-name _contact_pack aliases OK")

call = next(n for n in runner.body if isinstance(n, ast.Assign)
            and ast.unparse(n.targets[0]) == "_contact_pack" and isinstance(n.value, ast.Call))
assert sorted(k.arg for k in call.value.keywords) == sorted(EXPECTED_PARAMS)
assert all(ast.unparse(k.value) == k.arg for k in call.value.keywords), [ast.unparse(k.value) for k in call.value.keywords]
base_alias = max(n.lineno for n in runner.body if isinstance(n, ast.Assign)
                 and isinstance(n.targets[0], ast.Name)
                 and ast.unparse(n.value).startswith("_contact_base."))
facts_call = next(n for n in runner.body if isinstance(n, ast.Assign)
                  and ast.unparse(n.targets[0]) == "_stage2_facts" and isinstance(n.value, ast.Call))
assert base_alias < call.lineno < facts_call.lineno, (base_alias, call.lineno, facts_call.lineno)
assert all(a.lineno > call.end_lineno for a in aliases)
assert all(a.lineno < facts_call.lineno for a in aliases)
print("T0 binding and all 11 aliases sit between the base aliases and the facts factory OK")

assert 'Path(__file__).with_name("_contact_pack.py")' in runner_src
imported = {a.name for n in module.body if isinstance(n, ast.Import) for a in n.names}
imported |= {n.module or "" for n in module.body if isinstance(n, ast.ImportFrom)}
assert not any("contact_state" in name for name in imported), sorted(imported)
dotted = {ast.unparse(n) for n in ast.walk(module) if isinstance(n, ast.Attribute)}
assert not (dotted & {"sys.path", "sys.modules"}), sorted(dotted & {"sys.path", "sys.modules"})
dynamic = {"spec_from_file_location", "module_from_spec", "exec_module", "import_module"}
assert not {d for d in dotted if d.split(".")[-1] in dynamic}, sorted(dotted)
names_used = {n.id for n in ast.walk(module) if isinstance(n, ast.Name)}
assert not (names_used & {"__import__", "exec", "eval"}), sorted(names_used & {"__import__", "exec", "eval"})
from_names = {a.name for n in module.body if isinstance(n, ast.ImportFrom) for a in n.names}
assert not (from_names & dynamic), sorted(from_names & dynamic)
print("T0 runner loads it by path, and the module has no runner import and no dynamic-import names OK")

assert [n for n in runner.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in NAMES] == []
print("T0 none of the 11 names is defined at runner top level OK")
print("T0 CHECKS PASS")
PY
```
预期：`py_compile` 与 `--help` 无输出、退出码 0；脚本打印 5 条 `T0 ... OK` 与 1 条 `T0 CHECKS PASS`（共 6 行）。

2. T1–T3：取出对照基准、比对 `--help`、运行对比脚本与 docstring 核对：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-input-pack
RUN=/tmp/pc-stage9
mkdir -p "$RUN/base"
BASE_SHA=$(git rev-parse origin/refactor-shared-base)
git archive "$BASE_SHA" .apm/skills/professor-contact/scripts | tar -x -C "$RUN/base"
uv run --no-project python "$RUN/base/.apm/skills/professor-contact/scripts/contact_state.py" --help >"$RUN/help-base.txt"
diff -u "$RUN/help-base.txt" "$RUN/help-head.txt"
shasum -a 256 /tmp/pc-stage2-tools/compare_stage2_batch_v2.py
uv run --no-project /tmp/pc-stage2-tools/compare_stage2_batch_v2.py \
  "$RUN/base/.apm/skills/professor-contact/scripts" \
  .apm/skills/professor-contact/scripts \
  _contact_pack _contact_pack \
  _canonical_paper_record _merge_canonical_paper normalize_input_pack load_input_pack \
  _migrate_v1_candidate _slice_gap_directions _migrate_v1_cross_group normalize_candidate_state \
  load_candidate_state _strict_candidate_shape strict_candidate_state
```
> 第 2、5 步都从 `git rev-parse origin/refactor-shared-base` 取基准提交，堆栈自动 rebase 后无需改计划。当前值是 `3f590e8`（以 `git rev-parse origin/refactor-shared-base` 的输出为准）。

脚本来源 `/tmp/pc-stage2-tools/compare_stage2_batch_v2.py`，94 行，sha256 `1ba8c0f49346b1fa78c34fbeec4d82cdab206ebef6cbf1b629769f9e5e4346b6`。
预期：`diff` 无输出；63 条 `OK`（`T0` 3、`T1` 23、`T2` 14、`T3` 23），末尾 `ALL CHECKS PASS`，退出码 0。

   随后做 docstring 核对（只读）：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-input-pack
shasum -a 256 /tmp/pc-stage2-tools/check_docstrings_v3.py
uv run --no-project /tmp/pc-stage2-tools/check_docstrings_v3.py \
  /tmp/pc-stage9/base/.apm/skills/professor-contact/scripts \
  .apm/skills/professor-contact/scripts \
  contact_state.py _contact_pack.py \
  _canonical_paper_record _merge_canonical_paper normalize_input_pack load_input_pack \
  _migrate_v1_candidate _slice_gap_directions _migrate_v1_cross_group normalize_candidate_state \
  load_candidate_state _strict_candidate_shape strict_candidate_state
```
脚本 `/tmp/pc-stage2-tools/check_docstrings_v3.py`，109 行，sha256 `31c8b2081c5d1f5398d197d2992084f371d978d99084207a7a9e7f2880f29d4a`。
预期：**整行摘要**为 `total=11 with_doc=10 multi=9 clean_equal=10 without_doc=1 missing=0 mismatched=0` 且末行 `DOCSTRING CHECKS PASS`，退出码 0。注意脚本对“base 有、head 丢失”只把 `without_doc` 加一、退出码仍为 0，所以必须核对整行摘要，不能只看退出码。

3. T4：只跑清单列出的 10 个方法：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-input-pack/.apm/skills/professor-contact/tests
uv run --no-project python -m unittest \
  test_stage3_direction_identity.TestV2PackShape.test_pack_has_one_canonical_paper_record_per_item_key \
  test_stage3_direction_identity.TestV2PackShape.test_v1_pack_with_conflicting_shared_paper_fails_closed \
  test_stage3_direction_identity.TestV2PackShape.test_v1_pack_shared_paper_normalizes_to_one_record \
  test_stage3_direction_groups.Stage3DirectionGroupTests.test_stage4_exactly_migrates_v1_candidate_state_with_pack_mapping_without_stage3_rerun \
  test_stage3_direction_groups.Stage3DirectionGroupTests.test_stage4_same_professor_preserved_entry_needs_refresh_is_zero_write \
  test_issue66_stage3_local_state.Issue66LocalStateTests.test_rebuild_overview_only_migrates_a_unique_legacy_identity \
  test_contact_state.Issue67ProfessorLocalStage4Tests.test_02_professor_own_invalid_state_input_or_selection_writes_nothing \
  test_build_issue29_stage2_fixture.BuildIssue29Stage2FixtureTests.test_reuse_all_builds_the_accepted_state_contract \
  test_build_issue29_stage2_fixture.BuildIssue29Stage2FixtureTests.test_single_paper_builds_a_fresh_single_candidate_root \
  test_contact_state.TestRunnerBasics.test_05b_collection_key_limits_stage3 \
  -v
```
预期：`Ran 10 tests`、全部 `ok`；无 `skipped`／`FAIL`／`ERROR`。

4. T5：只跑清单列出的 2 个夹具方法：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-input-pack/.apm/skills/professor-contact/tests
uv run --no-project python -m unittest \
  test_stage5_immutable.TestWrapperKeepsInstalledLayoutLocator.test_finalize_through_wrapper_certifies_installed_layout_checker \
  test_stage5_dualtarget_contract.InstalledSharedSkillsLocatorTests.test_installed_shared_skills_layout_locator_finds_sibling \
  -v
```
预期：`Ran 2 tests`、全部 `ok`。

5. 失败处理：T4／T5 有方法失败时，只在父提交上对照**同一个方法**（不重跑整组），每次对照写独立日志、不覆盖既有记录。下面的块用 `METHOD` 环境变量指定方法，未指定时跑示例里那一个，因此可以原样执行：
```sh
set -e
METHOD="${METHOD:-test_stage3_direction_identity.TestV2PackShape.test_v1_pack_shared_paper_normalizes_to_one_record}"
BASE_SHA=$(git -C /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-input-pack rev-parse origin/refactor-shared-base)
BASELINE=/tmp/pc-stage9/base-${BASE_SHA:0:12}
LOG=/tmp/pc-stage9/baseline-${METHOD##*.}-$(date +%Y%m%d-%H%M%S).log
if [ ! -d "$BASELINE/.apm" ]; then
  mkdir -p "$BASELINE"
  git -C /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-input-pack archive "$BASE_SHA" | tar -x -C "$BASELINE"
fi
cd "$BASELINE/.apm/skills/professor-contact/tests"
uv run --no-project python -m unittest "$METHOD" -v >"$LOG" 2>&1 || true
cat "$LOG"
```
判据：父提交上同一个方法也失败＝既有失败；父提交通过而工作树失败＝本批回归。日志名带时间戳，同一方法反复对照也不覆盖；没有失败时不执行本步。

6. 失败注入：本批不适用。本批只搬移定义，不改事务、回滚、写入顺序或错误通道；必测清单里没有失败注入项。

7. 既有仓库检查（不属于本批必测项，也不作为通过条件）：PR 推送后引用 4 个 `shards` 与聚合 job `test` 的运行编号与结论。

## 不纳入本清单的范围

| 未纳入项 | 原因 |
| --- | --- |
| `stage5_output_*` 与 Stage 3／4／5 主体 | 属后续批次 |
| 全量套件的本地重跑 | 仓库 CI 已分片执行，不作为本批必测 |
| 新模块单独的可导入性单测 | T0 的直接执行、T3 的按路径加载与 T5 的复制加载已覆盖真实加载方式 |
| R6 的 diff 接缝与「常量值不变」 | R6 属实现侧 diff 核对（执行计划第 3 步）；常量值由 T4／T5 的 CLI 行为覆盖 |

## 修订记录

- 第 1 版：首次提交（含演练实测的 63 条 OK、10＋2 个方法与 docstring 期望值）。
- 第 2 版：按第一关意见修正——T4 换掉 3 个不执行本批定义的方法（换成候选状态 v1 迁移与保持条目的两个 `Stage3DirectionGroupTests` 方法、以及 `Issue66LocalStateTests` 的迁移方法），保留 `test_pack_has_one…` 并改称 stage2 输出契约；目标改成“输入包 v1 规范化、候选状态 v2 读取与 v1 迁移、严格形状”并写明 `_slice_gap_directions`／`_migrate_v1_cross_group` 只有 AST 覆盖的已知限制；T0 补“import 进来的动态名”与“14 个实参都是同名符号”两条断言；第 5 步改为按 SHA 建基准目录、日志名带方法短名；docstring 预期强调核对整行摘要。
- 第 3 版：按复核意见修正——第 3 步的方法命令同步成表里的新 10 个（删掉两个 `TestMigrate` 与越界用例，换成两个 `Stage3DirectionGroupTests` 迁移方法与 `Issue66LocalStateTests` 迁移方法），并重跑 T4；T4 行括号拆成“两个 `test_v1_pack_*` 直接调用、`test_pack_has_one_*` 是 stage2 输出契约”；T0 补 from-import 动态名断言；第 2 步也改为按 `origin/refactor-shared-base` 取基准。

## 审核状态

- 第 1 版：第一关 NEEDS_MODIFICATION（T4 有 4 个方法不执行本批定义、目标措辞不实）。
- 第 2 版：第一关 NEEDS_MODIFICATION（第 3 步命令未随表更新、T4 括号措辞）。
- 第 3 版：第一关 PASS；第二关 PASS（命令块与原文逐字一致、脚本哈希正确、期望与实际一致、失败处理只跑同一方法且日志独立）。
