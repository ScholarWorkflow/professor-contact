# 方向输入助手划分：profile、切片与跨组解析（测试计划）

## 版本、来源与状态

- 对应执行计划：[implementation-plan.md](implementation-plan.md)，计划第 2 版。
- Target repository revision: 工作分支 `refactor-direction-inputs`；对照基准为父提交 `972d4fd`（PR #126 的 head），命令里用 `git rev-parse origin/refactor-email-core` 动态取。
- Test plan revision: 第 3 版。
- 测试范围依据：`Test Engineer Rule.md`。

## 必测清单

| 编号 | 业务目标 | 输入 / 场景 | 预期结果 | 检查方式 |
| --- | --- | --- | --- | --- |
| T0 | 模块可编译、可加载，工厂契约与依赖注入正确（R1、R3、R4、R5） | 工作树 `scripts/contact_state.py`、`scripts/_direction_inputs.py` | `py_compile` 成功；`--help` 退出码 0；`build()` 参数精确等于 7 个名字、无位置参数、`kw_defaults` 全为 `None`；返回 6 个成员（成员集合固定为这 6 个；注入集合固定为 7 个参数名；两者各自按集合比较，顺序不作契约）；`_direction_inputs_module.build` 的 7 个关键字值都是同名 `Name` 且绑定发生在调用之前；6 个 runner 别名的值是 `_direction_inputs` 的同名属性，运行时 `is` 成立；绑定调用晚于 `PROFILE_INPUT_CHARS`（469）、早于全部 build 消费方（最早的是 `_candidate_validate`@930，另有 `_stage3_validation`@984、`_stage3_commands`@1088、`_stage4_commands`@1158、`_stage5_commands`@1424）；6 个名字不再在 runner 顶层定义；模块不导入 runner、无动态加载、不碰 `sys.path`／`sys.modules`、import 只有 `__future__`／`json`／`types`／`pathlib`／`typing` | 第 1 步命令；`T0 CHECKS PASS` |
| T1 | 6 个定义确实离开 runner 顶层（R1） | 对照基准与工作树 | base 仍定义 6 个、head 一个都不定义；模块存在；逐个“runner 已无 / 模块 `build()` 内有” | 第 2 步脚本的 `T0`／`T1` 行，共 16 条 `OK` |
| T2 | 搬移没有改变逻辑（R2） | 两侧源码 | 6 个定义的 AST 相同（比较时忽略 docstring）；docstring 3 个有（`_direction_slices` 9 行、`_cross_group_fresh` 3 行、`_parse_cross_groups` 6 行）、3 个没有；runner 其余函数/类定义不变；离开的是这 6 个；6 个都有别名 | 同一脚本的 `T2` 行（9 条 `OK`，与 T0／T1／T3 合计 38 条）+ 第 3 步 docstring 工具 |
| T3 | 旧接口与加载方式不变（R6） | 两侧 runner | 6 个名字都可调用、签名相同；`--help` 逐字节相同；整份脚本 38 条 `OK`（T0 3、T1 13、T2 9、T3 13） | 同一脚本的 `T3` 行 + 第 4 步 `HELP IDENTICAL` |
| T4 | 方向分组、跨组与切片的行为不变（R2、R4） | 4 个既有方法（均经真实 CLI 子进程）：`test_stage3_direction_groups.Stage3DirectionGroupTests.test_plan_groups_jobs_per_resolved_direction_with_exact_ids`、`test_explicit_cross_group_generates_separate_job_and_section`、`test_participant_change_invalidates_only_cross_group`、`test_cross_group_input_fail_closed` | 4 个方法全部 `ok`；每个方法经真实 CLI 子进程走到本批函数所在的方向分组与跨组解析路径（路径依据见下方覆盖说明；本步不断言调用次数） | 第 5 步命令；`Ran 4 tests`、`OK`。输出落 `/tmp/pc-stage20/t4.log` |
| T5 | 复制 runner 的既有夹具仍能加载新模块（R1、R5） | `test_stage5_immutable.TestWrapperKeepsInstalledLayoutLocator.test_finalize_through_wrapper_certifies_installed_layout_checker` | 该方法 `OK` 只证明复制布局含 `_direction_inputs.py` 并成功加载（夹具按 `RUNNER.parent.glob("_*.py")` 复制，runner 按路径加载、缺失即 `RuntimeError`）；方法内业务断言属 Stage 5，失败时按失败处理总则重跑本方法一次再判定 | 第 6 步命令；`Ran 1 test`、`OK`。输出落 `/tmp/pc-stage20/t5.log` |
| T6 | 接缝、常量值与文件尺寸可核对（R6、R7） | 工作树 `git status`、`git diff`、行数、顶层字面量赋值 | `git status --porcelain` 恰好 3 条：1 个 `M`（`contact_state.py`）、2 个 `??`（`_direction_inputs.py` 与 `plan/direction-inputs/`），没有其它改动；`git diff --stat` 为 `+28 −97`；`git diff --ignore-blank-lines -U0` 对 `contact_state.py` 是 6 个 hunk、默认上下文 2 个；runner 里 67 个顶层字面量赋值（常量）与父提交同名同值（`CONSTANTS UNCHANGED (67)`），搬移没有顺手改常量；runner 2154→2085 行、模块 130 行 | 第 7 步命令；第 8 步把结果写进执行记录 |

**覆盖说明**：T4 的 4 个方法都从 CLI 子进程（`helpers.raw_cli` 调 `stage3-plan` 与跨组输入）进入，命令分发把它们接到 stage3 计划与方向分组路径：读 profile 走 `load_profile_text`／`profile_fingerprint`，解析跨组与方向 ID 走 `_parse_cross_groups`／`_parse_direction_id_list`，跨组新鲜度走 `_cross_group_fresh`，岗位切片走 `_direction_slices`；`test_cross_group_input_fail_closed` 的 3 个子用例覆盖 `fail` 的两条 `invalid_params` 分支（少于 2 个 ID、未知 ID）。这里依据的是命令分发代码，不是调用计数。整份 `test_stage3_direction_groups` 19 个方法也全通过（不在必测清单内，只作旁证）。

**不新增的项（附理由）**：`fail` 的业务异常通道（`ProfessorBusinessFailure`）不新增——`fail` 是 runner 注入的既有对象，T0 已核对注入的是同一个名字，T4 的 `test_cross_group_input_fail_closed` 已走两条失败分支；`_cross_group_fresh` 的 `direction_fingerprints` 值类型分支不新增——6 个定义体 AST 与基线相同，逻辑差异不可能只出现在值类型上。原先列过的两项专用设施（进程内 32 组对照脚本、T4 调用次数插桩）已从本计划删除：它们属于为单个批次新增的专用对照与采集设施，未取得验收决定人批准，现有结构对照、docstring 核对与方法级 CLI 测试已足以判断清单内目标。

**失败处理总则**：任一步失败即停止后续必测项并保留终端输出（必要时 tee 到 `$RUN`）；同一必测项最多重跑 1 次，T4／T5 只重跑同一个失败方法；同一必测项连续失败 2 次即停止后续必测项，交计划负责人判定；不得修改输入、预期或换方法求通过。

**既有仓库检查（不属于本批业务必测清单）**：仓库 CI 的 4 个 `shards` 与聚合 job `test` 照常执行，不作为通过条件。

## 执行步骤

1. T0（编译、工厂契约、依赖注入、成员集合、模块源码约束）：
```sh
set -e
RUN=/tmp/pc-stage20
mkdir -p "$RUN"
(
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-direction-inputs
uv run --no-project python --version
uv run --no-project python -m py_compile \
  .apm/skills/professor-contact/scripts/contact_state.py \
  .apm/skills/professor-contact/scripts/_direction_inputs.py
uv run --no-project python .apm/skills/professor-contact/scripts/contact_state.py --help >"$RUN/help-head.txt"
uv run --no-project python - <<'PY'
import ast, inspect, importlib.util, sys
from pathlib import Path
S = Path(".apm/skills/professor-contact/scripts")
src = (S / "contact_state.py").read_text()
mod = (S / "_direction_inputs.py").read_text()
tree = ast.parse(src); mtree = ast.parse(mod)
build = next(n for n in mtree.body if isinstance(n, ast.FunctionDef) and n.name == "build")
params = [a.arg for a in build.args.kwonlyargs]
assert params == ["fail", "sha256_bytes", "truncate", "PROFILE_INPUT_CHARS",
                  "direction_machine_id", "direction_papers", "cross_group_id"], params
assert not build.args.args and build.args.defaults == [], "positional args present"
assert build.args.kw_defaults == [None] * 7, build.args.kw_defaults
assert all(isinstance(n, ast.FunctionDef) for n in build.body[:-1]), "build body is not defs + return"
ret = build.body[-1]
assert isinstance(ret, ast.Return), ast.dump(ret)
members = [k.arg for k in ret.value.keywords]
assert sorted(members) == sorted(["profile_fingerprint", "load_profile_text", "_direction_slices",
                                  "_cross_group_fresh", "_parse_direction_id_list",
                                  "_parse_cross_groups"]), members

def assignment(name):
    return next(n for n in tree.body
                if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
                and n.targets[0].id == name)
call = assignment("_direction_inputs").value
assert isinstance(call, ast.Call)
assert sorted([k.arg for k in call.keywords]) == sorted(params), [k.arg for k in call.keywords]
for k in call.keywords:
    assert isinstance(k.value, ast.Name) and k.value.id == k.arg, (k.arg, ast.dump(k.value))
    assert assignment(k.arg).lineno < call.lineno, k.arg
for name in members:
    a = assignment(name)
    assert isinstance(a.value, ast.Attribute) and isinstance(a.value.value, ast.Name)
    assert a.value.value.id == "_direction_inputs" and a.value.attr == name, (name, ast.dump(a.value))
const = assignment("PROFILE_INPUT_CHARS").lineno
candidate = assignment("_candidate_validate").value.lineno
stage3 = assignment("_stage3_commands").value.lineno
assert const < call.lineno < candidate < stage3, (const, call.lineno, candidate, stage3)
top = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
assert not (set(members) & top), set(members) & top
imports = sorted([a.name for n in ast.walk(mtree) if isinstance(n, ast.Import) for a in n.names] +
                 [n.module for n in ast.walk(mtree) if isinstance(n, ast.ImportFrom)])
assert imports == ["__future__", "json", "pathlib", "types", "typing"], imports
attrs = {(n.value.id, n.attr) for n in ast.walk(mtree)
         if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)}
assert not (attrs & {("sys", "path"), ("sys", "modules")}), attrs
assert "importlib" not in {n.id for n in ast.walk(mtree) if isinstance(n, ast.Name)}, "no dynamic loading"
spec = importlib.util.spec_from_file_location("_direction_inputs_probe", S / "_direction_inputs.py")
mod_obj = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod_obj)
assert len(inspect.signature(mod_obj.build).parameters) == 7
sp = importlib.util.spec_from_file_location("head_runner", S / "contact_state.py")
runner = importlib.util.module_from_spec(sp); sys.modules["head_runner"] = runner
sp.loader.exec_module(runner)
for name in members:
    assert getattr(runner, name) is getattr(runner._direction_inputs, name), name
print("T0 CHECKS PASS")
PY
)
```
预期：`T0 CHECKS PASS`，`--help` 退出码 0。说明：`members` 与 `params` 各自按集合比较，顺序只作展示、不作契约；契约是“6 个名字都有别名、别名与模块同名属性 `is` 同一”，顺序可调。

2. T1／T2／T3（A/B 结构、等价、入口）：
```sh
set -euo pipefail
RUN=/tmp/pc-stage20
WT=/Users/rekidunois/code/skill-repos-dev/worktrees/refactor-direction-inputs
TOOLS=/tmp/pc-stage2-tools
EXPECTED_BASE=972d4fd4b7f827fcac7b7305257f761e09ccc01b
test -f "$TOOLS/compare_stage2_batch_v2.py"
test "$(shasum -a 256 "$TOOLS/compare_stage2_batch_v2.py" | cut -d' ' -f1)" = \
  1ba8c0f49346b1fa78c34fbeec4d82cdab206ebef6cbf1b629769f9e5e4346b6
BASE=$(git -C "$WT" rev-parse origin/refactor-email-core)
test "$BASE" = "$EXPECTED_BASE"
rm -rf "$RUN/base" "$RUN/head" && mkdir -p "$RUN/base" "$RUN/head"
git -C "$WT" archive "$BASE" .apm/skills/professor-contact/scripts \
  | tar -x -C "$RUN/base" --strip-components=4
cp -R "$WT"/.apm/skills/professor-contact/scripts/. "$RUN/head"
rm -rf "$RUN/head/__pycache__"
cd "$RUN"
uv run --no-project "$TOOLS/compare_stage2_batch_v2.py" \
  base head _direction_inputs _direction_inputs_module \
  profile_fingerprint load_profile_text _direction_slices _cross_group_fresh \
  _parse_direction_id_list _parse_cross_groups | tee "$RUN/t1-t3.log"
```
预期：`ALL CHECKS PASS`，38 条 `OK`（T0 3、T1 13、T2 9、T3 13）。说明：`EXPECTED_BASE` 是 `git rev-parse origin/refactor-email-core` 的实测值（`972d4fd4b7f827fcac7b7305257f761e09ccc01b`），`test "$BASE" = "$EXPECTED_BASE"` 就是锁基线；基线变了本步必须报错而不是静默换基线。

3. docstring（T2 补充）：
```sh
set -euo pipefail
cd /tmp/pc-stage20
test -f /tmp/pc-stage2-tools/check_docstrings_v3.py
test "$(shasum -a 256 /tmp/pc-stage2-tools/check_docstrings_v3.py | cut -d' ' -f1)" = \
  31c8b2081c5d1f5398d197d2992084f371d978d99084207a7a9e7f2880f29d4a
uv run --no-project /tmp/pc-stage2-tools/check_docstrings_v3.py \
  base head contact_state.py _direction_inputs.py \
  profile_fingerprint load_profile_text _direction_slices _cross_group_fresh \
  _parse_direction_id_list _parse_cross_groups
```
预期：`total=6 with_doc=3 multi=3 clean_equal=3 without_doc=3 missing=0 mismatched=0` 与 `DOCSTRING CHECKS PASS`。

4. `--help` 逐字节（T3）：
```sh
set -euo pipefail
RUN=/tmp/pc-stage20
uv run --no-project python "$RUN/base/contact_state.py" --help >"$RUN/help-base.txt"
cmp "$RUN/help-base.txt" "$RUN/help-head.txt"
echo "HELP IDENTICAL"
```
预期：`HELP IDENTICAL`，无 `cmp` 差异输出。

5. T4（4 个方向分组方法）：
```sh
set -euo pipefail
RUN=/tmp/pc-stage20
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-direction-inputs/.apm/skills/professor-contact/tests
uv run --no-project python -m unittest \
  test_stage3_direction_groups.Stage3DirectionGroupTests.test_plan_groups_jobs_per_resolved_direction_with_exact_ids \
  test_stage3_direction_groups.Stage3DirectionGroupTests.test_explicit_cross_group_generates_separate_job_and_section \
  test_stage3_direction_groups.Stage3DirectionGroupTests.test_participant_change_invalidates_only_cross_group \
  test_stage3_direction_groups.Stage3DirectionGroupTests.test_cross_group_input_fail_closed \
  2>&1 | tee "$RUN/t4.log"
```
预期：`Ran 4 tests`、`OK`。

6. T5（复制布局加载新模块）：
```sh
set -euo pipefail
RUN=/tmp/pc-stage20
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-direction-inputs/.apm/skills/professor-contact/tests
uv run --no-project python -m unittest \
  test_stage5_immutable.TestWrapperKeepsInstalledLayoutLocator.test_finalize_through_wrapper_certifies_installed_layout_checker \
  2>&1 | tee "$RUN/t5.log"
```
预期：`Ran 1 test`、`OK`。

7. T6（接缝与文件尺寸）：
```sh
set -euo pipefail
WT=/Users/rekidunois/code/skill-repos-dev/worktrees/refactor-direction-inputs
cd "$WT"
git status --porcelain
git diff --stat
git diff --ignore-blank-lines -U0 -- .apm/skills/professor-contact/scripts/contact_state.py | grep -c '^@@'
git diff --ignore-blank-lines -- .apm/skills/professor-contact/scripts/contact_state.py | grep -c '^@@'
uv run --no-project python - <<'PY'
import ast, subprocess
from pathlib import Path
S = ".apm/skills/professor-contact/scripts/contact_state.py"
base = subprocess.run(["git", "show", "972d4fd:" + S],
                      capture_output=True, text=True, check=True).stdout
head = Path(S).read_text()

def literals(text):
    out = {}
    for n in ast.parse(text).body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1 \
                and isinstance(n.targets[0], ast.Name):
            try:
                out[n.targets[0].id] = ast.literal_eval(n.value)
            except (ValueError, SyntaxError):
                pass
    return out

base_const, head_const = literals(base), literals(head)
assert set(base_const) == set(head_const), set(base_const) ^ set(head_const)
changed = {k: (base_const[k], head_const[k])
           for k in base_const if base_const[k] != head_const[k]}
assert not changed, changed
print(f"CONSTANTS UNCHANGED ({len(base_const)})")
PY
wc -l .apm/skills/professor-contact/scripts/contact_state.py \
      .apm/skills/professor-contact/scripts/_direction_inputs.py
```
预期：`git status --porcelain` 恰好 3 条——1 个 `M`（`contact_state.py`）与 2 个 `??`（`_direction_inputs.py`、`plan/direction-inputs/`），没有其它改动；模块未跟踪，故 `git diff --stat` 只显示 `contact_state.py` 的 `+28 −97`；hunk 计数 6 与 2；顶层字面量赋值 67 个，父提交与工作树名字集合、值都相同（`CONSTANTS UNCHANGED (67)`），行级计数之外常量也没有被动过；行数 2085 与 130。

8. 记录（把结果写进执行记录）：
```sh
set -euo pipefail
WT=/Users/rekidunois/code/skill-repos-dev/worktrees/refactor-direction-inputs
cd "$WT"
git rev-parse HEAD
shasum -a 256 .apm/skills/professor-contact/scripts/contact_state.py \
  .apm/skills/professor-contact/scripts/_direction_inputs.py
```
预期：把第 1–7 步的输出、行数、两个文件的 sha256 与基线 sha 写进 `plan/direction-inputs/test-execution-2026-10-21.md`；记录里的每个值与当次命令输出逐字相同，不写推测值。

## 不纳入本清单的范围

| 未纳入项 | 原因 |
| --- | --- |
| verify 链、legacy 迁移 helper、`gap_job_block`／`assemble_followup_draft`／`load_validator_results`、stage1 三件套 | 后续批次，本批不搬移 |
| `_parse_cross_groups` 的重复组折叠顺序断言 | 只要求 base 与 head 相同（结构对照与 T4 的 CLI 方法覆盖），不新增业务预期 |
| 全量回归的逐条业务断言 | 仓库 CI 的 4 个 `shards` 覆盖，本清单只覆盖本批 6 个函数的调用链 |

## 修订记录

- 第 1 版：首次提交（含演练实测数据）。
- 第 2 版：按实跑结果校正 A/B 计数（T0 3、T1 13、T2 9、T3 13，共 38）。
- 第 3 版：按计划审核意见删去原 T5（进程内 32 组对照）与 T4 的插桩计数（未获批准的新增设施），原 T6／T7 顺次改为 T5／T6，步骤重排为 8 步（第 8 步记录结果）；基线 sha 随 #126 rebase 更新为 `972d4fd`，rebase 前后 `git diff` 为空；T2 计数改为 9 条；T0 不再把成员顺序当契约；T6 预期补上 `plan/direction-inputs/` 这条 `??`；失败处理补重跑上限；覆盖说明改为按命令分发路径陈述。复核后同版补：本文件头版本字段与执行计划指针同步；`_stage3_validation` 行号改为 head 的 984；第 1 步的成员与注入顺序断言改成集合比较；T6 增加“顶层字面量赋值与父提交同名同值”的观察点（R6 的不改常量值此前无观察面），第 7 步加对应命令。

## 审核状态

- 第 3 版：APPROVED（第 2 版意见 B4、B5、B6、B7、B8、B12、B17、B18 已修订；复核指出的 R1、R2、R3、R4 与 R6 的常量值观察点已在本版补齐，命令块有改动故整套重跑；复核后同版补齐 R1 的版本字段与 P3-a、P3-b、P3-c 三处文字，命令块逐字节未变，故未重跑）。Gate 1：PASS；Gate 2：PASS。
