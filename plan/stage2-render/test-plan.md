# Stage 2 划分第七批：渲染与校验层（测试计划）

## 版本、来源与状态

- 对应执行计划：[implementation-plan.md](implementation-plan.md)，计划第 3 版。
- Requirement revision: 第 1 版（2026-10-20 负责人要求）。
- Target repository revision: 工作分支 `refactor-stage2-render`；对照基准为当前 PR 基准分支 `main` 的提交 `6593beb0b8492d572fea6e707c29b039fdd1d7ef`（#113 已合并）。此前基准为 `c303242c79fd860302fcd95ac8f460a8e532bee2`、`2a2ffabe7a19e29be17b035a5c8a2e175fb6f81b`、`5972905`；已核对新旧基准相关 5 个程序文件 Git blob 相同，既有 T0–T5 通过结果继续有效。
- Test plan revision: 第 9 版（2026-10-20）。
- Review status: **第一关 PASS（沿用）；第二关第 9 版修订待复核；第三关既有 PASS 继续有效**（2026-10-20）。
- 测试范围依据：`Test Engineer Rule.md`。

## 必测清单

| 编号 | 业务目标 | 输入 / 场景 | 预期结果 | 检查方式 |
| --- | --- | --- | --- | --- |
| T0 | 模块可编译、可加载，两个工厂的契约与别名顺序正确（R1、R3、R4） | 工作树 `scripts/contact_state.py`、`scripts/_stage2_render.py`、`scripts/_stage2_finalize.py` | 三个文件 `py_compile` 成功；`--help` 退出码 0 且与父提交逐字节相同；`_stage2_render.build` 恰 16 个 keyword-only 参数、返回 12 个成员；`_stage2_finalize.build` 恰 40 个参数、返回 7 个成员；runner 有 12 个 `X = _stage2_render.X` 别名（去重后仍 12），其中包含两个标题 helper，且不再有指向 `_stage2_finalize` 的同名别名；模块不导入 runner、不做动态加载、不碰 `sys.path`／`sys.modules` | 第 1 步命令（7 条 `T0 ... OK` 与 `T0 CHECKS PASS`）；`--help` 的逐字节比较用第 2 步的 `diff -u` |
| T1 | 10 个定义确实离开 runner 顶层、进入模块 `build()`（R1） | 对照基准（`git archive 6593beb0` 取出的 `scripts`）与工作树 `scripts` | `T0`：base 与 head 是两个不同目录、base 仍定义 10 个定义、head 一个都不定义；`T1`：模块存在；10 个定义逐个“runner 顶层已无 / 模块 `build()` 内有” | 第 2 步对比脚本的 `T0 ...`／`T1 ...` 行，共 24 条 `OK` |
| T2 | 搬移没有改变任何逻辑（R2、R4） | 同上两侧源码，加基线 `_stage2_finalize.py` 与工作树 `_stage2_render.py` | 10 个定义的代码 AST 与基准相同（脚本忽略 docstring）；两个标题 helper 在 `_stage2_finalize.py` 中消失、在 `_stage2_render.py` 中出现且 AST 与基线版本相同；`_stage2_finalize.py` 其余 13 个函数 AST 不变；runner 其余顶层定义不变；离开 runner 的定义正好是这 10 个、没有新增；10 个名字都有 runner 别名 | 同一脚本的 `T2 ...` 行（13 条 `OK`）；标题 helper 用第 2 步第二段的只读 AST 核对 |
| T3 | 旧接口与加载方式不变（R3、R4、R5） | 同一进程内分别按文件路径加载两侧 runner；再以子进程直接执行改动后的 runner | 10 个名字在两侧都可调用、`inspect.signature` 相同；`--help` 退出码 0；runner 里两个加载块都用 `Path(__file__).with_name(...)` 指向模块文件（第 1 步断言）；`_stage2_render` 的 16 个实参与参数同名同集合、12 个别名都在调用之后 | 同一脚本的 `T3 ...` 行（21 条 `OK`）与第 1 步的源码约束核对；合计 58 条 `OK`、末尾 `ALL CHECKS PASS` |
| T4 | 渲染／校验层经命令的行为不变（R2、R4） | 7 个既有方法：`test_stage2_narrative_example_contract.NarrativeExampleContractTests` 的 3 个 `*_passes_finalize`；`test_stage2_resolved_direction.Stage2FinalizeWithResolvedTests` 的 3 个方法；`test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_business_rerender_and_bounded_correction_lifecycle` | **条件式通过条件**：7 个方法全部 `ok` 则 T4 通过；有失败时按第 5 步仅对照当前基准提交 `6593beb0` 上同一个实际失败的方法；父提交发生相同业务失败记既有失败（不计为 T4 通过），父提交通过而工作树发生业务失败记本批回归；环境或测试运行故障记无法判断 | 第 3 步命令；`Ran 7 tests`、`OK`，无 skip／`FAIL`／`ERROR` |
| T5 | 复制 runner 的既有夹具仍能加载新模块 | `test_stage5_immutable.TestWrapperKeepsInstalledLayoutLocator.test_finalize_through_wrapper_certifies_installed_layout_checker`、`test_stage5_dualtarget_contract.InstalledSharedSkillsLocatorTests.test_installed_shared_skills_layout_locator_finds_sibling` | 复制布局包含 `_stage2_render.py`，复制后的 runner 能按路径加载它；两方法 `OK` | 第 4 步命令；`Ran 2 tests`、`OK` |

**既有仓库检查（不属于本批业务必测清单）**：仓库 CI 的 4 个 `shards` 与聚合 job `test` 照常执行，结果按运行编号与 head 单独引用；本批不在本地重跑全量套件。

## 执行步骤

准备与执行都在工作树 `/Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage2-render` 内进行；临时脚本与运行产物放仓库外 `/tmp/pc-stage7`。

1. T0：编译、直接执行、两个工厂的契约与模块源码约束（同一命令块，`set -e`）。该块放在 0 缩进，`<<'PY'` 的结束行可按原样执行。
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage2-render
RUN=/tmp/pc-stage7
mkdir -p "$RUN"
uv run --no-project python --version
uv run --no-project python -m py_compile \
  .apm/skills/professor-contact/scripts/contact_state.py \
  .apm/skills/professor-contact/scripts/_stage2_render.py \
  .apm/skills/professor-contact/scripts/_stage2_finalize.py
uv run --no-project python .apm/skills/professor-contact/scripts/contact_state.py --help >"$RUN/help-head.txt"
uv run --no-project python - <<'PY'
import ast
from pathlib import Path

scripts = Path(".apm/skills/professor-contact/scripts")
runner = ast.parse((scripts / "contact_state.py").read_text())
render_src = (scripts / "_stage2_render.py").read_text()
render = ast.parse(render_src)
finalize = ast.parse((scripts / "_stage2_finalize.py").read_text())

def members_of(module, name):
    build = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == name)
    returned = next(n for n in ast.walk(build)
                    if isinstance(n, ast.Return) and isinstance(n.value, ast.Call)
                    and ast.unparse(n.value.func).endswith("SimpleNamespace"))
    return build, [k.arg for k in returned.value.keywords]

render_build, render_members = members_of(render, "build")
expected = {"fail", "GAP_STATUSES", "PLACEHOLDER_RE", "now_utc", "read_json_file", "truncate",
            "rel_path", "filename_component", "direction_machine_id", "pack_paper_index",
            "direction_papers", "direction_relevant_keys", "direction_provisional_member_keys",
            "shortlist_size", "Stage2Context", "Stage2PackRefineContext"}
args = {a.arg for a in render_build.args.kwonlyargs}
assert args == expected, (sorted(args), sorted(expected - args), sorted(args - expected))
assert not render_build.args.args and not render_build.args.vararg and not render_build.args.kwarg
assert len(render_members) == 12 and len(set(render_members)) == 12, render_members
print("T0 render build takes exactly the 16 keyword-only parameters OK")
print("T0 render build returns 12 members OK")

finalize_build, finalize_members = members_of(finalize, "build")
assert len(finalize_build.args.kwonlyargs) == 40, len(finalize_build.args.kwonlyargs)
assert len(finalize_members) == 7 and len(set(finalize_members)) == 7, finalize_members
assert not (set(finalize_members) & {"stage2_trusted_paper_title",
                                     "stage2_require_later_paper_titles"})
print("T0 finalize build takes 40 parameters and returns 7 members OK")

aliases = [n for n in runner.body if isinstance(n, ast.Assign)
           and isinstance(n.targets[0], ast.Name)
           and ast.unparse(n.value).startswith("_stage2_render.")]
assert len(aliases) == 12 and len({n.targets[0].id for n in aliases}) == 12, len(aliases)
assert all(ast.unparse(n.value) == "_stage2_render." + n.targets[0].id for n in aliases)
for name in ("stage2_trusted_paper_title", "stage2_require_later_paper_titles"):
    assert any(a.targets[0].id == name for a in aliases), name
    old = [n for n in runner.body if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
           and n.targets[0].id == name and ast.unparse(n.value).startswith("_stage2_finalize.")]
    assert not old, name
print("T0 runner aliases the 12 render members and no longer points the titles at finalize OK")

call = next(n for n in runner.body if isinstance(n, ast.Assign)
            and isinstance(n.value, ast.Call)
            and ast.unparse(n.value.func) == "_stage2_render_module.build")
assert sorted(k.arg for k in call.value.keywords) == sorted(expected)
assert all(a.lineno > call.end_lineno for a in aliases)
print("T0 runner injects the same 16 names and puts all 12 aliases after the call OK")

imported = {a.name for n in render.body if isinstance(n, ast.Import) for a in n.names}
imported |= {n.module or "" for n in render.body if isinstance(n, ast.ImportFrom)}
assert not any("contact_state" in name for name in imported), sorted(imported)
dotted = {ast.unparse(n) for n in ast.walk(render) if isinstance(n, ast.Attribute)}
assert not (dotted & {"sys.path", "sys.modules"}), sorted(dotted & {"sys.path", "sys.modules"})
dynamic = {"spec_from_file_location", "module_from_spec", "exec_module", "import_module"}
assert not {d for d in dotted if d.split(".")[-1] in dynamic}, sorted(dotted)
runner_src = (scripts / "contact_state.py").read_text()
for stem in ("_stage2_render", "_stage2_finalize"):
    assert f'Path(__file__).with_name("{stem}.py")' in runner_src, stem
print("T0 runner loads both modules by path next to itself OK")

print("T0 render module imports no runner, loads nothing dynamically, touches no sys.path/sys.modules OK")
print("T0 CHECKS PASS")
PY
```
预期：`py_compile` 与 `--help` 无输出、退出码 0；脚本打印 7 条 `T0 ... OK` 与 `T0 CHECKS PASS`。

2. T1–T3：取出对照基准并运行对比脚本，随后做标题 helper 的模块间 AST 核对：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage2-render
RUN=/tmp/pc-stage7
mkdir -p "$RUN/base"
git archive 6593beb0b8492d572fea6e707c29b039fdd1d7ef .apm/skills/professor-contact/scripts | tar -x -C "$RUN/base"
uv run --no-project python "$RUN/base/.apm/skills/professor-contact/scripts/contact_state.py" --help >"$RUN/help-base.txt"
diff -u "$RUN/help-base.txt" "$RUN/help-head.txt"
shasum -a 256 /tmp/pc-stage2-tools/compare_stage2_batch_v2.py
uv run --no-project /tmp/pc-stage2-tools/compare_stage2_batch_v2.py \
  "$RUN/base/.apm/skills/professor-contact/scripts" \
  .apm/skills/professor-contact/scripts \
  _stage2_render _stage2_render \
  validate_freshness_results narrative_scope validate_narrative_entry validate_narrative \
  citation_render rendered_markdown_block_lines render_positioning_block redact_item_keys \
  build_direction_pack render_analysis_md
```
脚本来源 `/tmp/pc-stage2-tools/compare_stage2_batch_v2.py`，94 行，sha256 `1ba8c0f49346b1fa78c34fbeec4d82cdab206ebef6cbf1b629769f9e5e4346b6`；缺失或哈希不同时停止。
预期：`diff` 无输出；58 条 `OK`（`T0` 3、`T1` 21、`T2` 13、`T3` 21），末尾 `ALL CHECKS PASS`，退出码 0。

   随后核对两个标题 helper 的模块间搬移（同一份两侧源码，只读）：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage2-render
uv run --no-project python - <<'PY'
import ast
from pathlib import Path

base_dir = Path("/tmp/pc-stage7/base/.apm/skills/professor-contact/scripts")
head_dir = Path(".apm/skills/professor-contact/scripts")
targets = ("stage2_trusted_paper_title", "stage2_require_later_paper_titles")

def nested(module_path):
    tree = ast.parse(module_path.read_text())
    build = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "build")
    return {n.name: n for n in ast.walk(build)
            if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name != "build"}

def strip_docs(node):
    clone = ast.parse(ast.unparse(node))
    for parent in ast.walk(clone):
        body = getattr(parent, "body", None)
        if isinstance(body, list) and body and isinstance(body[0], ast.Expr) \
                and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
            body[0] = ast.Expr(value=ast.Constant(value="<DOC>"))
    return clone

base_finalize = nested(base_dir / "_stage2_finalize.py")
head_finalize = nested(head_dir / "_stage2_finalize.py")
head_render = nested(head_dir / "_stage2_render.py")
for name in targets:
    assert name in base_finalize, name
    assert name in head_render, name
    assert name not in head_finalize, name
    assert ast.dump(strip_docs(base_finalize[name])) == ast.dump(strip_docs(head_render[name])), name
print("T0 titles helpers moved from finalize to render with identical AST OK")
assert set(base_finalize) - set(head_finalize) == set(targets), set(base_finalize) - set(head_finalize)
for name, node in head_finalize.items():
    assert name in base_finalize, name
    assert ast.dump(strip_docs(base_finalize[name])) == ast.dump(strip_docs(node)), name
print("T0 remaining finalize helpers keep their AST OK")
PY
```
预期：2 条 `T0 ... OK`、退出码 0。

3. T4：只跑清单列出的 7 个方法：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage2-render/.apm/skills/professor-contact/tests
uv run --no-project python -m unittest \
  test_stage2_narrative_example_contract.NarrativeExampleContractTests.test_codex_example_passes_finalize \
  test_stage2_narrative_example_contract.NarrativeExampleContractTests.test_opencode_example_passes_finalize \
  test_stage2_narrative_example_contract.NarrativeExampleContractTests.test_plan_example_passes_finalize \
  test_stage2_resolved_direction.Stage2FinalizeWithResolvedTests.test_finalize_applies_resolved_directions_to_pack \
  test_stage2_resolved_direction.Stage2FinalizeWithResolvedTests.test_finalize_stamps_resolved_subfield_on_unchanged_directions \
  test_stage2_resolved_direction.Stage2FinalizeWithResolvedTests.test_finalize_fails_closed_on_stale_resolved_file \
  test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_business_rerender_and_bounded_correction_lifecycle \
  -v
```
预期：`Ran 7 tests`、全部 `ok`；无 `skipped`／`FAIL`／`ERROR`。

4. T5：只跑清单列出的 2 个夹具方法：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage2-render/.apm/skills/professor-contact/tests
uv run --no-project python -m unittest \
  test_stage5_immutable.TestWrapperKeepsInstalledLayoutLocator.test_finalize_through_wrapper_certifies_installed_layout_checker \
  test_stage5_dualtarget_contract.InstalledSharedSkillsLocatorTests.test_installed_shared_skills_layout_locator_finds_sibling \
  -v
```
预期：`Ran 2 tests`、全部 `ok`。

5. 失败处理：仅在 T4／T5 有方法失败时执行。先把第 3／4 步中**实际失败的完整测试方法名**设为环境变量 `METHOD`，然后执行本命令块；未设置则立即报错停止，不默认选择其他方法。每次只在父提交上运行该方法，不重跑整组；保存独立日志和退出码。
```sh
set -e
: "${METHOD:?须传入 T4/T5 实际失败的完整测试方法名}"
RUN=/tmp/pc-stage7
mkdir -p "$RUN"
LOG="$(mktemp "$RUN/baseline-XXXXXXXX")"
BASELINE="$RUN/base-6593beb0"
if [ ! -d "$BASELINE/.apm" ]; then
  mkdir -p "$BASELINE"
  git -C /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage2-render archive 6593beb0b8492d572fea6e707c29b039fdd1d7ef | tar -x -C "$BASELINE"
fi
cd "$BASELINE/.apm/skills/professor-contact/tests"
if uv run --no-project python -m unittest "$METHOD" -v >"$LOG" 2>&1; then
  BASELINE_EXIT=0
else
  BASELINE_EXIT=$?
fi
cat "$LOG"
printf '对照退出码：%s；日志路径：%s\n' "$BASELINE_EXIT" "$LOG"
```
判据：只对比同一方法的实际业务结果。父提交与工作树出现相同业务失败，记既有失败（不得算通过）；父提交通过而工作树出现业务失败，记本批回归；若观察到依赖缺失、测试启动失败或环境故障，记无法判断，不以退出码非零直接认定既有业务失败。`mktemp` 为每次尝试生成不同日志路径，保留所有正式尝试；没有失败时不执行本步，不新增用例。

6. 失败注入：本批不适用。本批只搬移定义并把两个标题 helper 换到渲染模块，不修改事务、回滚、写入顺序或错误通道实现；必测清单里没有失败注入项。

7. 既有仓库检查（不属于本批必测项，也不作为通过条件）：PR 推送后引用 4 个 `shards` 与聚合 job `test` 的运行编号与结论。

## 不纳入本清单的范围

| 未纳入项 | 原因 |
| --- | --- |
| 方向解析 helper 与 Stage 3 主体 | 属后续批次 |
| 全量套件的本地重跑 | 仓库 CI 已分片执行，不作为本批必测 |
| 新模块单独的可导入性单测 | T0 的直接执行、T3 的按路径加载与 T5 的两条复制加载路径已覆盖真实加载方式 |

## 修订记录

- 第 1 版：首次提交。
- 第 2 版：按实施前演练补齐 `Stage2PackRefineContext`，修正为 16 个注入参数，更新对照基准与期望输出。
- 第 3 版：处理第一关原有 K1–K5：核对加载方式、检查条数、失败处理覆盖与工具哈希；T0–T5 必测项不变。
- 第 4—5 版：分别记录第一关、原第二关审核意见；未增加必测项。第二关后续复核提出的 K1、K2 按第 6 版处理。
- 第 6 版：对照基准改为 `2a2ffabe`；失败对照改为只运行失败的单个方法，日志独立保存；既有 T0–T5 结果复用。
- 第 7 版：修复第 5 步方法占位符导致的 shell 语法错误，补实测记录。
- 第 8 版：T4 与第 5 步统一为相同方法对照；要求 `METHOD` 指明实际失败方法、保留退出码，并区分业务失败和环境／测试错误；对照基准更新为 `c303242c`，同步版本记录。必测清单和原始 T0–T5 执行结果不变。
- 第 9 版：#113 合并后 PR 基准更新为 `6593beb0`；同步修订版本说明、T1／T4 的基准引用及第 2／5 步的 `git archive` 命令和第 5 步目录名。新旧基准的 5 个相关程序文件 Git blob 一致；本批的程序和测试文件均未改变，复用 T0–T5 既有结果。

## 审核状态

- 第一关：**PASS**（复用既有结论）。
- 第二关：**第 9 版修订待复核**；只复核基准引用、第 2／5 步及其直接影响的版本说明。
- 第三关：**既有 PASS 继续有效**。此前 T0–T5 已审核通过；本轮只修订基准引用和说明，相关程序与测试文件 Git blob 未变，按规则第 6 节复用，不重跑。
