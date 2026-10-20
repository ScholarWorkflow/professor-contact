# 邮件核心划分：邮箱条目编译（测试计划）

## 版本、来源与状态

- 对应执行计划：[implementation-plan.md](implementation-plan.md)，计划第 2 版。
- Target repository revision: 工作分支 `refactor-email-core`；对照基准为父提交 `3ffdab0`（PR #125 的 head），命令里用 `git rev-parse origin/refactor-shared-helpers` 动态取。
- Test plan revision: 第 3 版。
- 测试范围依据：`Test Engineer Rule.md`。

## 必测清单

| 编号 | 业务目标 | 输入 / 场景 | 预期结果 | 检查方式 |
| --- | --- | --- | --- | --- |
| T0 | 模块可编译、可加载，工厂契约与依赖注入正确（R1、R3、R4、R5） | 工作树 `scripts/contact_state.py`、`scripts/_email_core.py`、`scripts/_stage5_email.py` | `py_compile` 成功；`--help` 退出码 0；`build()` 参数精确等于 5 个名字、无位置参数、`kw_defaults` 全为 `None`；返回 4 个成员；`_email_core_module.build` 的 5 个关键字值都是同名 `Name` 且绑定发生在调用之前；4 个 runner 别名的值都是 `_email_core` 的同名属性，运行时 `is` 成立；绑定调用晚于 `EMAIL_SOURCE_HASH_FIELDS`（1125）、早于 `_stage4_commands` 的 build（1227）；`_stage5_email.build` 是 12 个参数、`kw_defaults` 全 `None`；`_stage5_email.py` 全文 0 处 `email_source_hash`；3 个名字不再在 runner 顶层定义；模块不导入 runner、无动态加载、不碰 `sys.path`／`sys.modules` | 第 1 步命令；`T0 CHECKS PASS` |
| T1 | 3 个定义确实离开 runner 顶层（R1） | 对照基准与工作树 | base 仍定义 3 个、head 一个都不定义；模块存在；逐个“runner 已无 / 模块 `build()` 内有” | 第 2 步脚本的 `T0`／`T1` 行，共 10 条 `OK` |
| T2 | 搬移没有改变逻辑（R2） | 两侧源码 | 3 个定义的 AST 相同（比较时忽略 docstring）；docstring 3 个都有（2 个多行）清洗后同文；runner 其余函数/类定义不变；离开的是这 3 个；3 个都有别名；`email_source_hash` 定义体 AST 相同 | 同一脚本的 `T2` 行（6 条 `OK`）+ 第 3 步 docstring（`total=3 with_doc=3 multi=2 clean_equal=3`）+ 第 4 步 hash 专项 |
| T3 | 旧接口与加载方式不变（R3、R4、R5） | 两侧 runner | 3 个名字都可调用、签名相同；`--help` 逐字节相同；`email_source_hash` 两侧可调用、签名相同、同一输入同哈希、runner 别名与模块命名空间是同一对象（`is`）；脚本 **23 条 `OK`**（T0 3、T1 7、T2 6、T3 7），hash 专项另 4 条（AST、同哈希、`is`、签名） | 同一脚本的 `T3` 行（7 条 `OK`）+ 第 4 步（`HELP IDENTICAL`、`EMAIL SOURCE HASH CHECKS PASS`） |
| T4 | 邮箱条目编译与选择解析的行为不变（R2） | 7 个既有方法（均经真实 CLI 子进程）：`test_contact_state.TestRunnerBasics` 的 5 个（`test_06_email_pack_exact_join_only`、`test_06b_papers_override_controls_email_order`、`test_06c_invalid_papers_override_does_not_write`、`test_06f_stage4_preserves_previous_direction_selection`、`test_10_email_pack_self_contained`）、`test_contact_state.TestStage5.test_done_by_self_gap_banned_in_source_map`、`test_contact_state.Issue67AdjacentStateTests.test_08_cross_selection_scope_refreshes_every_participating_direction` | **条件式通过条件**：7 个方法全部 `ok` 则通过；有失败时按第 5 步只对照**同一个失败方法**。实际调用链：`stage4-finalize` 与 `stage4-migrate-local` 两个入口都经 `stage4_professor_transaction → _stage4_professor_commit` 到达本批函数；`_selection_direction_ids` 在 `validate_stage4_selections:84`、commit 的 `:240`（legacy `collection_key`，`test_06f` 第一次 finalize 走这里）与 `:258`（既有行 explicit）调用；`validate_papers_override` 在 `:141`、`:368`；`compile_email_entry` 在 `:371`。T4 用 finalize 作为足够入口，migrate-local 不另测；第 7 个方法覆盖跨方向组分支（插桩实测 `group=True participants=True` 1 次） | 第 5 步命令；`Ran 7 tests`、`OK`。输出落 `/tmp/pc-stage18/t4.log` |
| T5 | 复制 runner 的既有夹具仍能加载新模块（R1、R5） | `test_stage5_immutable.TestWrapperKeepsInstalledLayoutLocator.test_finalize_through_wrapper_certifies_installed_layout_checker` | 该方法 `OK` 只证明复制布局含 `_email_core.py` 并成功加载（夹具按 `RUNNER.parent.glob("_*.py")` 复制，runner 在 368–374 行按路径加载、缺失即 `RuntimeError`）；方法内业务断言属 Stage 5，失败时按第 6 步单方法对照 | 第 6 步命令；`Ran 1 test`、`OK`。输出落 `/tmp/pc-stage18/t5.log` |

**覆盖证据**：T4 的 7 个方法在插桩副本上运行的实际调用次数为 `_selection_direction_ids` 21 次、`validate_papers_override` 17 次、`compile_email_entry` 8 次（7 次单方向 + 1 次跨方向组）、`email_source_hash` 8 次；跨方向方法同时执行 `group_entry` 与 `participant_directions` 分支。插桩只在副本 `/tmp/pc-stage18/wt3` 上做，工作树源码不含插桩。

**不新增的项（附理由）**：`validate_papers_override` 的非 list、空串、未知 key 三个失败分支不新增——函数体 AST 与基线相同，唯一外部依赖 `fail` 已由 `test_06c` 的重复 key 分支证明，新增需写新用例；`stage4-migrate-local` 不新增用例——与 finalize 共用同一组绑定函数，本计划只修正入口陈述；复制布局缺模块的负向用例不新增——缺失已是 `RuntimeError`，正向复制足够。

**失败处理总则**：任一步失败即停止后续必测项并保留终端输出（必要时 tee 到 `$RUN`）；T4／T5 只重跑同一个失败方法；不得修改输入、预期或换方法求通过。

**既有仓库检查（不属于本批业务必测清单）**：仓库 CI 的 4 个 `shards` 与聚合 job `test` 照常执行，不作为通过条件。

## 执行步骤

1. T0（编译、工厂契约、依赖注入、别名顺序、模块源码约束）：
```sh
set -e
RUN=/tmp/pc-stage18
mkdir -p "$RUN"
(
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-email-core
uv run --no-project python --version
uv run --no-project python -m py_compile \
  .apm/skills/professor-contact/scripts/contact_state.py \
  .apm/skills/professor-contact/scripts/_email_core.py \
  .apm/skills/professor-contact/scripts/_stage5_email.py
uv run --no-project python .apm/skills/professor-contact/scripts/contact_state.py --help >"$RUN/help-head.txt"
uv run --no-project python - <<'PY'
import ast, inspect, importlib.util, sys
from pathlib import Path
S = Path(".apm/skills/professor-contact/scripts")
src = (S / "contact_state.py").read_text()
mod = (S / "_email_core.py").read_text()
s5src = (S / "_stage5_email.py").read_text()
tree = ast.parse(src); mtree = ast.parse(mod)
build = next(n for n in mtree.body if isinstance(n, ast.FunctionDef) and n.name == "build")
params = [a.arg for a in build.args.kwonlyargs]
assert params == ["fail", "direction_machine_id", "direction_papers",
                  "EMAIL_SOURCE_HASH_FIELDS", "sha256_obj"], params
assert not build.args.args and build.args.defaults == [], "positional args present"
assert build.args.kw_defaults == [None] * 5, build.args.kw_defaults
ret = next(n for n in ast.walk(build) if isinstance(n, ast.Return))
members = [k.arg for k in ret.value.keywords]
assert members == ["email_source_hash", "compile_email_entry",
                   "validate_papers_override", "_selection_direction_ids"], members

def assignment(name):
    return next(n for n in tree.body
                if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
                and n.targets[0].id == name)
call = assignment("_email_core").value
assert isinstance(call, ast.Call)
assert [k.arg for k in call.keywords] == params, [k.arg for k in call.keywords]
for k in call.keywords:
    assert isinstance(k.value, ast.Name) and k.value.id == k.arg, (k.arg, ast.dump(k.value))
    assert assignment(k.arg).lineno < call.lineno, k.arg
for name in members:
    a = assignment(name)
    assert isinstance(a.value, ast.Attribute) and isinstance(a.value.value, ast.Name)
    assert a.value.value.id == "_email_core" and a.value.attr == name, (name, ast.dump(a.value))
fields = assignment("EMAIL_SOURCE_HASH_FIELDS").lineno
stage4 = assignment("_stage4_commands").value.lineno
stage5 = assignment("_stage5_email").value.lineno
assert fields < call.lineno < stage4 < stage5, (fields, call.lineno, stage4, stage5)
top = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
assert not ({"compile_email_entry", "validate_papers_override", "_selection_direction_ids"} & top)
assert "email_source_hash" not in s5src, "stage5_email still references email_source_hash"
s5 = ast.parse(s5src)
s5b = next(n for n in s5.body if isinstance(n, ast.FunctionDef) and n.name == "build")
assert len(s5b.args.kwonlyargs) == 12 and s5b.args.kw_defaults == [None] * 12
imports = [a.name for n in ast.walk(mtree) if isinstance(n, ast.Import) for a in n.names] + \
          [n.module for n in ast.walk(mtree) if isinstance(n, ast.ImportFrom)]
assert sorted(imports) == ["__future__", "pathlib", "types", "typing"], imports
attrs = {(n.value.id, n.attr) for n in ast.walk(mtree)
         if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)}
assert not (attrs & {("sys", "path"), ("sys", "modules")}), attrs
names = {n.id for n in ast.walk(mtree) if isinstance(n, ast.Name)}
assert "spec_from_file_location" not in names
spec = importlib.util.spec_from_file_location("_email_core_probe", S / "_email_core.py")
mod_obj = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod_obj)
assert len(inspect.signature(mod_obj.build).parameters) == 5
sp = importlib.util.spec_from_file_location("head_runner", S / "contact_state.py")
runner = importlib.util.module_from_spec(sp); sys.modules["head_runner"] = runner
sp.loader.exec_module(runner)
for name in members:
    assert getattr(runner, name) is getattr(runner._email_core, name), name
assert "email_source_hash" not in vars(runner._stage5_email)
print("T0 CHECKS PASS")
PY
)
```
预期：`T0 CHECKS PASS`，`--help` 退出码 0。说明：`members` 与 `params` 按顺序比较是刻意为之——别名顺序与工厂参数顺序属于既有契约，重排视为接缝变化。

2. T1／T2／T3（A/B 结构、等价、入口）：
```sh
set -euo pipefail
RUN=/tmp/pc-stage18
WT=/Users/rekidunois/code/skill-repos-dev/worktrees/refactor-email-core
TOOLS=/tmp/pc-stage2-tools
EXPECTED_BASE=3ffdab0352fcc72a64c24dc5ec5c114d7de47179
test -f "$TOOLS/compare_stage2_batch_v2.py"
test "$(shasum -a 256 "$TOOLS/compare_stage2_batch_v2.py" | cut -d' ' -f1)" = \
  1ba8c0f49346b1fa78c34fbeec4d82cdab206ebef6cbf1b629769f9e5e4346b6
BASE=$(git -C "$WT" rev-parse origin/refactor-shared-helpers)
test "$BASE" = "$EXPECTED_BASE"
rm -rf "$RUN/base" "$RUN/head" && mkdir -p "$RUN/base" "$RUN/head"
git -C "$WT" archive "$BASE" .apm/skills/professor-contact/scripts \
  | tar -x -C "$RUN/base" --strip-components=4
cp -R "$WT"/.apm/skills/professor-contact/scripts/. "$RUN/head"
rm -rf "$RUN/head/__pycache__"
cd "$RUN"
uv run --no-project "$TOOLS/compare_stage2_batch_v2.py" \
  base head _email_core _email_core_module \
  compile_email_entry validate_papers_override _selection_direction_ids | tee "$RUN/t1-t3.log"
```
预期：`ALL CHECKS PASS`，23 条 `OK`（T0 3、T1 7、T2 6、T3 7）。

3. docstring（T2 补充）：
```sh
set -euo pipefail
cd /tmp/pc-stage18
test -f /tmp/pc-stage2-tools/check_docstrings_v3.py
test "$(shasum -a 256 /tmp/pc-stage2-tools/check_docstrings_v3.py | cut -d' ' -f1)" = \
  31c8b2081c5d1f5398d197d2992084f371d978d99084207a7a9e7f2880f29d4a
uv run --no-project /tmp/pc-stage2-tools/check_docstrings_v3.py \
  base head contact_state.py _email_core.py \
  compile_email_entry validate_papers_override _selection_direction_ids
```
预期：`total=3 with_doc=3 multi=2 clean_equal=3 without_doc=0 missing=0 mismatched=0` 与 `DOCSTRING CHECKS PASS`。

4. `--help` 逐字节与 `email_source_hash` 专项（T3）：
```sh
set -e
RUN=/tmp/pc-stage18
uv run --no-project python "$RUN/base/contact_state.py" --help >"$RUN/help-base.txt"
diff -u "$RUN/help-base.txt" "$RUN/help-head.txt" && echo "HELP IDENTICAL"
uv run --no-project python - <<'PY'
import ast, importlib.util, inspect, sys
from pathlib import Path
RUN = Path("/tmp/pc-stage18")
def nested(path, name):
    tree = ast.parse(Path(path).read_text())
    b = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "build")
    return next(n for n in b.body if isinstance(n, ast.FunctionDef) and n.name == name)
def strip_docs(node):
    clone = ast.parse(ast.unparse(node))
    for parent in ast.walk(clone):
        body = getattr(parent, "body", None)
        if isinstance(body, list) and body and isinstance(body[0], ast.Expr) \
                and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
            body[0] = ast.Expr(value=ast.Constant(value="<DOC>"))
    return clone
assert ast.dump(strip_docs(nested(RUN / "base/_stage5_email.py", "email_source_hash"))) == \
       ast.dump(strip_docs(nested(RUN / "head/_email_core.py", "email_source_hash")))
def load(p, n):
    spec = importlib.util.spec_from_file_location(n, p)
    m = importlib.util.module_from_spec(spec); sys.modules[n] = m
    spec.loader.exec_module(m); return m
base = load(RUN / "base/contact_state.py", "esh_base")
head = load(RUN / "head/contact_state.py", "esh_head")
entry = {k: k for k in ("email_id", "direction_ids", "directions", "idea", "papers",
                        "gaps", "red_lines", "allowed_sources", "contact_evidence",
                        "cross_direction")}
assert base.email_source_hash(entry) == head.email_source_hash(entry)
assert head.email_source_hash is head._email_core.email_source_hash
assert str(inspect.signature(base.email_source_hash)) == str(inspect.signature(head.email_source_hash))
print("EMAIL SOURCE HASH CHECKS PASS")
PY
```
预期：`HELP IDENTICAL`、`EMAIL SOURCE HASH CHECKS PASS`。

5. T4（邮箱编译与选择解析）：
```sh
set -euo pipefail
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-email-core/.apm/skills/professor-contact/tests
uv run --no-project python -m unittest -v \
  test_contact_state.TestRunnerBasics.test_06_email_pack_exact_join_only \
  test_contact_state.TestRunnerBasics.test_06b_papers_override_controls_email_order \
  test_contact_state.TestRunnerBasics.test_06c_invalid_papers_override_does_not_write \
  test_contact_state.TestRunnerBasics.test_06f_stage4_preserves_previous_direction_selection \
  test_contact_state.TestRunnerBasics.test_10_email_pack_self_contained \
  test_contact_state.TestStage5.test_done_by_self_gap_banned_in_source_map \
  test_contact_state.Issue67AdjacentStateTests.test_08_cross_selection_scope_refreshes_every_participating_direction \
  2>&1 | tee /tmp/pc-stage18/t4.log
```
预期：`Ran 7 tests`、`OK`。

6. T5（复制布局加载新模块）：
```sh
set -euo pipefail
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-email-core/.apm/skills/professor-contact/tests
uv run --no-project python -m unittest -v \
  test_stage5_immutable.TestWrapperKeepsInstalledLayoutLocator.test_finalize_through_wrapper_certifies_installed_layout_checker \
  2>&1 | tee /tmp/pc-stage18/t5.log
```
预期：`Ran 1 test`、`OK`。

7. 接缝核对（R7）：
```sh
set -euo pipefail
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-email-core
git status --short
git diff --stat
git diff --ignore-blank-lines -U0 -- .apm/skills/professor-contact/scripts/contact_state.py | grep -c '^@@'
git diff --ignore-blank-lines -U0 -- .apm/skills/professor-contact/scripts/_stage5_email.py | grep -c '^@@'
wc -l .apm/skills/professor-contact/scripts/contact_state.py \
      .apm/skills/professor-contact/scripts/_email_core.py \
      .apm/skills/professor-contact/scripts/_stage5_email.py
```
预期：`git status --short` 为 2 个已改文件（`_stage5_email.py`、`contact_state.py`）+ 2 个未跟踪项（`scripts/_email_core.py`、`plan/email-core/`）。`_email_core.py` 未跟踪，所以 `git diff --stat` 只统计已跟踪文件，显示 `+26 −213`；runner 4 个 hunk、`_stage5_email.py` 3 个 hunk；行数 2154／234／499。

## 不纳入本清单的范围

| 未纳入项 | 原因 |
| --- | --- |
| `assemble_followup_draft` | 依赖 `stage5_recipient_authority`，下一批单独处理 |
| contact evidence、stage1、profile/direction、verify 链、legacy 迁移 helper | 后续批次 |
| 全量回归的逐条业务断言 | 仓库 CI 的 4 个 `shards` 覆盖，本清单只覆盖本批 4 个函数的调用链 |

## 修订记录

- 第 1 版：首次提交。
- 第 2 版：按第一关审核修正——T0 补 `kw_defaults`、绑定实参同名 `Name`、4 个别名运行时 `is`、`_stage5_email.py` 零引用与 12 参数检查；T4 改为 7 个方法并修正入口与 `:240` legacy 位置、新增跨方向方法；T5 精简为 1 个方法；T3 写明“脚本 23 条 + hash 专项 4 条”；第 5／6 步加 `set -euo pipefail`；第 7 步限定 hunk 路径并说明未跟踪模块不计入 `git diff --stat`。
- 第 3 版：按第二关修正——第 2 步改 `set -euo pipefail` 并锁定 `BASE=3ffdab0…`、校验 compare 工具 sha256、复制后清 `__pycache__`；第 3 步加 docstring 工具校验；第 7 步加 `set -euo pipefail`；补失败处理总则。

## 审核状态

- 第 1 版：第一关 NEEDS_MODIFICATION（T0 注入检查不完整、T4 入口陈述错误、T5 重复、计数口径）。
- 第 2 版：第一关 `Gate 1 conclusion: PASS`；第二关 NEEDS_MODIFICATION（第 2 步缺 `pipefail`、base ref 未锁定、工具未做前置检查、第 7 步缺 `pipefail`、`__pycache__` 未清理）。
- 第 3 版：第二关 `Gate 2 conclusion: PASS`。
