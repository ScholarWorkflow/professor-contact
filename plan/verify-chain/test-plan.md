# 校验链三函数划分（测试计划）

## 版本、来源与状态

- 对应执行计划：[implementation-plan.md](implementation-plan.md)，计划第 4 版。
- Test plan revision: 第 3 版。
- Proposed review status: pending。
- Target repository revision: 工作分支 `refactor-verify-chain`，父提交 `58c71c02cd0b6d66aae4cda5b7cc815431a461e6`；工作树 `/Users/rekidunois/code/skill-repos-dev/worktrees/refactor-verify-chain`。
- 测试范围依据：`Test Engineer Rule.md`；只验证本批搬移没有改变行为，不重新设计业务规则。

## 必测清单

| 编号 | 覆盖的验收条件 | 业务目标 | 输入 / 场景 | 预期结果 | 检查方式 |
| --- | --- | --- | --- | --- | --- |
| T0 | R1、R3、R4、R5 的结构部分 | 新模块可加载，工厂契约正确 | 两个脚本、`build()` 的 AST 与运行时签名 | 6 个 keyword-only 参数、无位置参数、无默认值；3 个成员；6 个实参都是同名 `Name`；绑定在 6 个依赖之后、`_stage5_commands` 之前；别名与模块属性同一对象；`build()` 内每个成员恰好 1 个 `FunctionDef` | 第 1 步 Python 断言与运行时导入；另含第 2 步的 3 条 T0 前置 |
| T1 | R1 | 三个函数确实离开 runner | 父提交与 head 的 runner | runner 顶层定义 3 → 0；模块存在 | 第 2 步 A/B 工具，T0 前置 3 条 + T1 7 条 = 10 条 `OK` |
| T2 | R2 | 搬移没有改函数体、注释与 docstring | 三个函数的 AST，忽略 docstring；模块符号表；父提交 1200–1297 的源码文本 | 三对函数体 AST 相等；其余顶层定义不变；只搬走这三个；3 个别名存在；`total=3 with_doc=1 multi=0 clean_equal=1 without_doc=2 missing=0 mismatched=0`；94 行源码去掉缩进后逐行相同，12 行 Issue-#10 注释都在；三个函数的对外名字只剩导入名、兄弟函数与注入名 | 第 2 步 A/B 工具 6 条 `OK`；第 3 步 docstring 工具、`symtable` 与源码文本核对 |
| T3 | R6 的帮助输出 | 运行时接口不变 | 两个 runner 的 `--help` 与函数签名 | 三个函数仍可调用；`--help` 退出 0 且逐字节相同（3221 字节、sha256 `d622b7e6…`） | 第 2 步 A/B 工具 7 条 `OK`；第 4 步 `cmp` 与 sha256 断言 |
| T4 | R6 的缓存契约 | 校验缓存契约不变 | `stage5-plan` 的真实 CLI 子进程，3 个既有方法 | 成功、4 种格式不兼容、mtime 漂移、31 天过期都被原样拒绝；`Ran 3 tests`、`OK` | 第 5 步 `unittest` |
| T5 | R6 的安装布局 | 安装布局下的 wrapper 仍能完成 finalize | `test_stage5_immutable` 的既有用例 | `Ran 1 test`、`OK` | 第 6 步 `unittest` |
| T6 | R6、R7 | 接缝与常量没有夹带 | git diff、帮助、runner 与模块行数 | 2 个 hunk；`+27 −98`；67 个常量不变；状态恰好 3 项；执行前清掉旧缓存、执行后工作树没有 `__pycache__`；runner 2014 行、模块 129 行只作观察值记录 | 第 7 步 git 与 Python 检查 |

任何一步失败都停下，不得跳步或只跑一部分；修复后从失败的那一步重新执行，重试上限与停止条件见“失败处理”小节。仓库检查只读：不修改测试代码、不新增依赖、不提交；执行产生的日志只写到 `/tmp/pc-stage21/`。

## 执行步骤

### 第 1 步：T0 模块编译、工厂契约与绑定位置

```sh
set -euo pipefail
WT=/Users/rekidunois/code/skill-repos-dev/worktrees/refactor-verify-chain
S="$WT/.apm/skills/professor-contact/scripts"
RUN=/tmp/pc-stage21
EXPECTED_BASE="58c71c02cd0b6d66aae4cda5b7cc815431a461e6"
mkdir -p "$RUN"
export PYTHONPYCACHEPREFIX="$RUN/pycache"
rm -rf "$S/__pycache__" "$WT/.apm/skills/professor-contact/tests/__pycache__"
test "$(git -C "$WT" rev-parse HEAD)" = "$EXPECTED_BASE"
cd "$WT"
uv run --no-project python -m py_compile "$S/contact_state.py" "$S/_verify_chain.py"
uv run --no-project python "$S/contact_state.py" --help > "$RUN/help-head.txt"
uv run --no-project python - <<'PY'
import ast
import importlib.util
import inspect
import sys
from pathlib import Path

S = Path(".apm/skills/professor-contact/scripts")
runner_src = (S / "contact_state.py").read_text()
module_src = (S / "_verify_chain.py").read_text()
runner_tree = ast.parse(runner_src)
module_tree = ast.parse(module_src)
members = ["_fingerprint_failure_kind", "_verify_diagnostic_failure", "verify_state"]
params = [
    "read_json_file",
    "VERIFY_TTL_DAYS",
    "VERIFY_TIMESTAMP_FORMAT",
    "VERIFY_FILE",
    "email_item_is_evidence_seeded",
    "current_source_fingerprints",
]

build = next(
    node for node in module_tree.body
    if isinstance(node, ast.FunctionDef) and node.name == "build"
)
actual_params = [arg.arg for arg in build.args.kwonlyargs]
assert sorted(actual_params) == sorted(params), actual_params
assert build.args.args == [] and build.args.defaults == []
assert build.args.kw_defaults == [None] * 6, build.args.kw_defaults
assert len(build.body) == 4, ast.dump(build.body[-1])
assert all(isinstance(node, ast.FunctionDef) for node in build.body[:3])
returned = build.body[-1]
assert isinstance(returned, ast.Return)
assert sorted(keyword.arg for keyword in returned.value.keywords) == sorted(members)
for name in members:
    definitions = [
        node for node in ast.walk(build)
        if isinstance(node, ast.FunctionDef) and node.name == name
    ]
    assert len(definitions) == 1, (name, len(definitions))


def assignment(name):
    for node in runner_tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and target.id == name:
                return node
    raise AssertionError(f"missing assignment: {name}")


call = assignment("_verify_chain").value
assert isinstance(call, ast.Call)
assert sorted(keyword.arg for keyword in call.keywords) == sorted(params)
for keyword in call.keywords:
    assert isinstance(keyword.value, ast.Name), ast.dump(keyword.value)
    assert keyword.value.id == keyword.arg
    assert assignment(keyword.arg).lineno < call.lineno

for name in members:
    alias = assignment(name)
    assert isinstance(alias.value, ast.Attribute), ast.dump(alias.value)
    assert isinstance(alias.value.value, ast.Name)
    assert alias.value.value.id == "_verify_chain"
    assert alias.value.attr == name
    assert call.lineno < alias.lineno

stage5 = assignment("_stage5_commands").value
assert call.lineno < stage5.lineno

top_level = {node.name for node in runner_tree.body if isinstance(node, ast.FunctionDef)}
assert not (set(members) & top_level), sorted(set(members) & top_level)

imports = []
for node in module_tree.body:
    if isinstance(node, ast.ImportFrom):
        imports.append(node.module)
    elif isinstance(node, ast.Import):
        imports.extend(alias.name for alias in node.names)
assert sorted(imports) == ["__future__", "datetime", "pathlib", "types", "typing"], imports

for node in ast.walk(module_tree):
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        assert not (node.value.id == "sys" and node.attr in {"path", "modules"})
    if isinstance(node, ast.Name):
        assert node.id not in {"__import__"}
imported = {a.name for n in ast.walk(module_tree) if isinstance(n, ast.Import)
            for a in n.names}
imported |= {n.module for n in ast.walk(module_tree) if isinstance(n, ast.ImportFrom)}
assert "importlib" not in imported and "sys" not in imported, imported

spec = importlib.util.spec_from_file_location("_verify_chain_probe", S / "_verify_chain.py")
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
signature = inspect.signature(module.build)
assert len(signature.parameters) == 6
assert all(p.kind is inspect.Parameter.KEYWORD_ONLY for p in signature.parameters.values())
assert all(p.default is inspect.Parameter.empty for p in signature.parameters.values())

runner_spec = importlib.util.spec_from_file_location("head_runner", S / "contact_state.py")
assert runner_spec is not None and runner_spec.loader is not None
runner = importlib.util.module_from_spec(runner_spec)
sys.modules["head_runner"] = runner
runner_spec.loader.exec_module(runner)
for name in members:
    assert getattr(runner, name) is getattr(runner._verify_chain, name)
print("T0 CHECKS PASS")
PY
```

预期：`py_compile` 无输出；`--help` 退出 0；最后一行 `T0 CHECKS PASS`。此步覆盖 R1、R3、R4、R5 的结构部分。开头的 `rm -rf` 清掉上一条运行留下的旧缓存，`PYTHONPYCACHEPREFIX` 把本次编译缓存写到 `/tmp/pc-stage21/pycache`，工作树不新增 `__pycache__`。

### 第 2 步：T1–T3 父提交与 head 的 A/B 等价

```sh
set -euo pipefail
WT=/Users/rekidunois/code/skill-repos-dev/worktrees/refactor-verify-chain
TOOLS=/tmp/pc-stage2-tools
RUN=/tmp/pc-stage21
S=.apm/skills/professor-contact/scripts
EXPECTED_BASE="58c71c02cd0b6d66aae4cda5b7cc815431a461e6"
export PYTHONPYCACHEPREFIX="$RUN/pycache"
test -f "$TOOLS/compare_stage2_batch_v2.py"
test "$(wc -l < "$TOOLS/compare_stage2_batch_v2.py" | tr -d ' ')" -eq 94
test "$(shasum -a 256 "$TOOLS/compare_stage2_batch_v2.py" | cut -d' ' -f1)" = \
  1ba8c0f49346b1fa78c34fbeec4d82cdab206ebef6cbf1b629769f9e5e4346b6
BASE=$(git -C "$WT" rev-parse HEAD)
test "$BASE" = "$EXPECTED_BASE"
rm -rf "$RUN/base" "$RUN/head"
mkdir -p "$RUN/base" "$RUN/head"
git -C "$WT" archive "$BASE" "$S" | tar -x -C "$RUN/base" --strip-components=4
cp -R "$WT/$S/." "$RUN/head/"
rm -rf "$RUN/base/__pycache__" "$RUN/head/__pycache__"
uv run --no-project "$TOOLS/compare_stage2_batch_v2.py" \
  "$RUN/base" "$RUN/head" _verify_chain _verify_chain_module \
  _fingerprint_failure_kind _verify_diagnostic_failure verify_state \
  | tee "$RUN/t1-t3.log"
```

预期：退出 0；输出 23 条 `OK`（T0 3、T1 7、T2 6、T3 7），最后一行 `ALL CHECKS PASS`。工具 94 行、sha256 `1ba8c0f49346b1fa78c34fbeec4d82cdab206ebef6cbf1b629769f9e5e4346b6`，缺失、行数或哈希不同即停止；该工具与第 18 批 `plan/email-core/test-plan.md` 用的是同一个文件，不是本批新增设施。

### 第 3 步：docstring、自由名字与源码文本核对

```sh
set -euo pipefail
RUN=/tmp/pc-stage21
export PYTHONPYCACHEPREFIX="$RUN/pycache"
test -f /tmp/pc-stage2-tools/check_docstrings_v3.py
test "$(wc -l < /tmp/pc-stage2-tools/check_docstrings_v3.py | tr -d ' ')" -eq 109
test "$(shasum -a 256 /tmp/pc-stage2-tools/check_docstrings_v3.py | cut -d' ' -f1)" = \
  31c8b2081c5d1f5398d197d2992084f371d978d99084207a7a9e7f2880f29d4a
uv run --no-project /tmp/pc-stage2-tools/check_docstrings_v3.py \
  "$RUN/base" "$RUN/head" contact_state.py _verify_chain.py \
  _fingerprint_failure_kind _verify_diagnostic_failure verify_state \
  | tee "$RUN/docstrings.log"
uv run --no-project python - <<'PY'
import builtins
import symtable
from pathlib import Path

source = Path("/tmp/pc-stage21/head/_verify_chain.py").read_text()
top = symtable.symtable(source, "_verify_chain.py", "exec")
build = next(child for child in top.get_children() if child.get_name() == "build")
functions = {child.get_name(): child for child in build.get_children()
             if child.get_type() == "function"}
assert set(functions) == {"_fingerprint_failure_kind", "_verify_diagnostic_failure",
                          "verify_state"}, set(functions)
builtin_names = set(dir(builtins))


def external(table):
    return {symbol.get_name() for symbol in table.get_symbols()
            if (symbol.is_global() or symbol.is_free())
            and symbol.get_name() not in builtin_names}


assert external(functions["_fingerprint_failure_kind"]) == set()
assert external(functions["_verify_diagnostic_failure"]) == set()
assert external(functions["verify_state"]) == {
    "VERIFY_FILE", "VERIFY_TIMESTAMP_FORMAT", "VERIFY_TTL_DAYS",
    "_fingerprint_failure_kind", "_verify_diagnostic_failure",
    "current_source_fingerprints", "datetime", "email_item_is_evidence_seeded",
    "read_json_file", "timedelta", "timezone",
}
print("FREE NAMES OK")
PY
uv run --no-project python - <<'PY'
from pathlib import Path

base = Path("/tmp/pc-stage21/base/contact_state.py").read_text().splitlines()
module = Path("/tmp/pc-stage21/head/_verify_chain.py").read_text().splitlines()
removed = [line.strip() for line in base[1199:1297] if line.strip()]
start = next(i for i, line in enumerate(module)
             if line.strip().startswith("def _fingerprint_failure_kind"))
end = next(i for i, line in enumerate(module)
           if line.strip().startswith("return types.SimpleNamespace"))
moved = [line.strip() for line in module[start:end] if line.strip()]
assert removed == moved, "source text differs beyond indentation"
comments = [line.strip() for line in base[1199:1297] if line.lstrip().startswith("#")]
assert len(comments) == 12, len(comments)
assert [line.strip() for line in module[start:end] if line.lstrip().startswith("#")] == comments
print(f"SOURCE TEXT IDENTICAL ({len(moved)} lines, {len(comments)} comments)")
PY
```

预期：`total=3 with_doc=1 multi=0 clean_equal=1 without_doc=2 missing=0 mismatched=0`，并输出 `DOCSTRING CHECKS PASS`、`FREE NAMES OK`、`SOURCE TEXT IDENTICAL (94 lines, 12 comments)`。检查器 109 行、sha256 `31c8b2081c5d1f5398d197d2992084f371d978d99084207a7a9e7f2880f29d4a`，缺失或哈希不同即停止。自由名字用 `symtable` 核对：`_fingerprint_failure_kind` 与 `_verify_diagnostic_failure` 只剩内建名，`verify_state` 只剩 3 个模块导入（`datetime`、`timedelta`、`timezone`）、2 个兄弟函数和 6 个注入名；`from __future__ import annotations` 让注解不参与运行时自由名字。源码文本核对把父提交 1200–1297 与模块搬移段都去掉行首缩进与行尾空白、忽略空行后逐行比较（94 行），并单独按顺序比较 12 行注释；空行位置允许因搬移变化，覆盖 AST 看不见的注释。

### 第 4 步：两个 runner 的帮助输出逐字节一致

```sh
set -euo pipefail
RUN=/tmp/pc-stage21
export PYTHONPYCACHEPREFIX="$RUN/pycache"
uv run --no-project python "$RUN/base/contact_state.py" --help > "$RUN/help-base.txt"
cmp "$RUN/help-base.txt" "$RUN/help-head.txt"
test "$(wc -c < "$RUN/help-base.txt" | tr -d ' ')" -eq 3221
test "$(shasum -a 256 "$RUN/help-base.txt" | cut -d' ' -f1)" = \
  d622b7e69794bb81b04f456c642f82bc72eab7c9f1e197fb4c44a2ece7157c03
shasum -a 256 "$RUN/help-base.txt"
```

预期：`cmp` 无输出；字节数 3221；sha256 为 `d622b7e69794bb81b04f456c642f82bc72eab7c9f1e197fb4c44a2ece7157c03`，三项都由命令断言，不符即失败。

### 第 5 步：T4 校验缓存契约的 3 个既有方法

```sh
set -euo pipefail
WT=/Users/rekidunois/code/skill-repos-dev/worktrees/refactor-verify-chain
RUN=/tmp/pc-stage21
export PYTHONPYCACHEPREFIX="$RUN/pycache"
cd "$WT/.apm/skills/professor-contact/tests"
uv run --no-project python -m unittest -v \
  test_issue81_verify_cache_contract.Issue81VerifyCacheContractTests.test_a_actual_plan_hints_seed_a_reusable_complete_cache \
  test_issue81_verify_cache_contract.Issue81VerifyCacheContractTests.test_b_noncanonical_values_keep_the_reason_and_report_the_field \
  test_issue81_verify_cache_contract.Issue81VerifyCacheContractTests.test_c_changed_mtime_and_31_day_cache_remain_rejected \
  2>&1 | tee "$RUN/t4.log"
```

预期：退出 0；`Ran 3 tests`；最后一行 `OK`。三个方法都通过 `helpers.raw_cli("stage5-plan", ...)` 启动真实子进程，不直接调用 `verify_state`。

### 第 6 步：T5 安装布局 wrapper 的既有方法

```sh
set -euo pipefail
WT=/Users/rekidunois/code/skill-repos-dev/worktrees/refactor-verify-chain
RUN=/tmp/pc-stage21
export PYTHONPYCACHEPREFIX="$RUN/pycache"
cd "$WT/.apm/skills/professor-contact/tests"
uv run --no-project python -m unittest -v \
  test_stage5_immutable.TestWrapperKeepsInstalledLayoutLocator.test_finalize_through_wrapper_certifies_installed_layout_checker \
  2>&1 | tee "$RUN/t5.log"
```

预期：退出 0；`Ran 1 test`；最后一行 `OK`。

### 第 7 步：T6 接缝、常量与尺寸

```sh
set -euo pipefail
WT=/Users/rekidunois/code/skill-repos-dev/worktrees/refactor-verify-chain
S=.apm/skills/professor-contact/scripts
RUN=/tmp/pc-stage21
export PYTHONPYCACHEPREFIX="$RUN/pycache"
cd "$WT"
EXPECTED_BASE="58c71c02cd0b6d66aae4cda5b7cc815431a461e6"
BASE=$(git rev-parse HEAD)
test "$BASE" = "$EXPECTED_BASE"
git status --porcelain | tee "$RUN/status.txt"
test "$(git status --porcelain | wc -l | tr -d ' ')" -eq 3
grep -q '^ M \.apm/skills/professor-contact/scripts/contact_state\.py$' "$RUN/status.txt"
grep -q '^?? \.apm/skills/professor-contact/scripts/_verify_chain\.py$' "$RUN/status.txt"
grep -q '^?? plan/verify-chain/$' "$RUN/status.txt"
test -z "$(find "$S" "$WT/.apm/skills/professor-contact/tests" -name __pycache__ -print -quit)"
git diff --stat | tee "$RUN/diff-stat.txt"
grep -q '1 file changed, 27 insertions(+), 98 deletions(-)' "$RUN/diff-stat.txt"
test "$(git diff --ignore-blank-lines -U0 -- "$S/contact_state.py" | grep -c '^@@')" -eq 2
test "$(git diff --ignore-blank-lines -- "$S/contact_state.py" | grep -c '^@@')" -eq 2
git diff --ignore-blank-lines -U0 -- "$S/contact_state.py" | grep '^@@'
export BASE
uv run --no-project python - <<'PY'
import ast
import os
import subprocess

S = ".apm/skills/professor-contact/scripts/contact_state.py"
BASE = os.environ["BASE"]


def literals(source):
    found = {}
    for node in ast.parse(source).body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        try:
            found[target.id] = ast.literal_eval(node.value)
        except Exception:
            continue
    return found


base_src = subprocess.run(
    ["git", "show", f"{BASE}:{S}"], check=True, capture_output=True, text=True
).stdout
base_literals = literals(base_src)
head_literals = literals(open(S).read())
assert base_literals == head_literals
assert len(base_literals) == 67, len(base_literals)
print(f"CONSTANTS UNCHANGED ({len(base_literals)})")
PY
printf 'parent runner: %s lines\n' "$(git show "$BASE:$S/contact_state.py" | wc -l | tr -d ' ')"
printf 'head runner:   %s lines\n' "$(wc -l < "$S/contact_state.py" | tr -d ' ')"
printf 'module:        %s lines\n' "$(wc -l < "$S/_verify_chain.py" | tr -d ' ')"
```

预期：状态恰好 3 项（`M contact_state.py`、`?? _verify_chain.py`、`?? plan/verify-chain/`）；`scripts/` 与 `tests/` 下没有 `__pycache__`；diff 统计为 `1 file changed, 27 insertions(+), 98 deletions(-)`，两组 hunk 计数都是 2，这两项是 R7 的通过条件；hunk 头为 `@@ -1200,98 +1200,11 @@` 与 `@@ -1386,0 +1300,16 @@`；输出 `CONSTANTS UNCHANGED (67)`；三行 `printf` 记录 2085、2014、129，只作观察值，不进判定。若行数出现差异但 diff 统计与 hunk 数仍符合，记录差异原因即可；diff 统计或 hunk 数不符才是失败。

### 第 8 步：执行记录

```sh
set -euo pipefail
WT=/Users/rekidunois/code/skill-repos-dev/worktrees/refactor-verify-chain
S=.apm/skills/professor-contact/scripts
cd "$WT"
git rev-parse HEAD
test "$(git rev-parse HEAD)" = "58c71c02cd0b6d66aae4cda5b7cc815431a461e6"
shasum -a 256 "$S/contact_state.py" "$S/_verify_chain.py"
test "$(shasum -a 256 "$S/contact_state.py" | cut -d' ' -f1)" = \
  acc1ab20929c25376552c7f53bd2a48b5aad4331ec32ded9ce44f9e43a6fdcbb
test "$(shasum -a 256 "$S/_verify_chain.py" | cut -d' ' -f1)" = \
  512acbead24f4550792131ebeed9afdede6d7f734ed8db364ae5d6a201dc27ea
```

预期：HEAD 等于 `58c71c02cd0b6d66aae4cda5b7cc815431a461e6`；两个 sha256 分别等于 `acc1ab20929c25376552c7f53bd2a48b5aad4331ec32ded9ce44f9e43a6fdcbb` 与 `512acbead24f4550792131ebeed9afdede6d7f734ed8db364ae5d6a201dc27ea`，三项都由 `test` 断言，不符即失败。把本步输出、第 2 步的 23 条 `OK`、第 5 步的 `Ran 3 tests`、第 6 步的 `Ran 1 test` 写入 `test-execution-<日期>.md`。

## 失败处理

- T0 失败：先看是编译、`build()` 契约、绑定顺序还是运行时导入；不要用“先跑测试再说”绕过，结构不成立时业务通过也不能算通过。
- A/B 失败：按工具输出的 T0／T1／T2／T3 分类定位。T1 失败通常是 `FunctionDef` 没搬干净；T2 失败是函数体被改；T3 失败是签名或帮助输出变了。
- docstring 或源码文本失败：只允许补回原文，不允许改写措辞；`_fingerprint_failure_kind` 的 docstring 必须逐字一致，12 行注释一行都不能少。
- T4／T5 失败：保存完整子进程输出，确认失败发生在 `stage5-plan` 的真实调用链上；不得改成直接调用 `verify_state` 的测试来“绕过”。
- T6 失败：先看 `git status` 是否混入日志、`__pycache__` 或测试产物；再看 hunk 数，空行收敛错误通常表现为 1 个或 3 个 hunk。

### 重试与停止

- 只重试测试调用链之外的基础设施故障：`uv` 无法启动或下载、工具文件不可读、解释器启动失败。业务断言失败（A/B 计数、docstring、源码文本、`unittest`、help、diff、常量、状态）不重试；行数只记录，不参与判定。
- 同一步骤最多尝试 2 次（首次加 1 次重跑）；第 2 次仍失败就停止，受影响项记为未通过或无法判断，不换方法、不改预期求通过。
- 重跑第 2 步前删除它派生的 `$RUN/base`、`$RUN/head`，旧日志改名为 `*-attempt1.log` 保留；重跑第 3、4 步时保留 `base/head`（它们是第 2 步的输入），只在需要重建时先重跑第 2 步。输入、预期与工具保持不变。
- 改变输入、工具或断言属于方案修订，要写进修订记录并整套重跑，不能标成同条件重试。

## 判定口径与覆盖说明

- **T4 的 3 个方法**：`test_a` 覆盖完整缓存加指纹匹配的成功路径；`test_b` 用 4 个 subTest 覆盖 `float-mtime`、`alternate-path`、`fractional-time`、`offset-time`，分别落到 `stale_fingerprint` 与 `bad_timestamp`，诊断字段为 `source_fingerprints.info_json`、`source_fingerprints.boshu_analysis`、`verified_at`；`test_c` 覆盖 `recorded_mtime_mismatch` 与 `age_expired`。合计 7 条路径。
- **调用链**：3 个方法都通过 `helpers.raw_cli("stage5-plan", ...)` 启动真实子进程，命令分发后在 `_stage5_commands` 中调用 `verify_state`；head 的消费方是 `_stage5_commands.build(..., verify_state=verify_state, ...)`（父提交 1424／1454 行）。`verify_state` 内部再调用 `read_json_file`、`current_source_fingerprints`、`_fingerprint_failure_kind`、`_verify_diagnostic_failure`。
- **注入名覆盖**：`read_json_file`、`VERIFY_FILE`、`VERIFY_TTL_DAYS`、`VERIFY_TIMESTAMP_FORMAT`、`current_source_fingerprints`、`_fingerprint_failure_kind`、`_verify_diagnostic_failure` 都在上述 7 条路径中被实际执行；`email_item_is_evidence_seeded` 只在 `decision.status` 为 `escalate` 或 `needs_refresh` 的分支使用，本批 7 条路径没有触发。T0 已核对它是 runner 自己的对象，R2 的 AST 相等与源码文本核对保证函数体未变，因此不另造业务场景。
- **T5 的作用**：`test_stage5_immutable` 的该方法从安装布局入口执行 wrapper，能发现“模块按相对路径加载失败”这类只在包装层出现的问题；它不替代 T4 对 `verify_state` 分支的覆盖。
- **T6 的作用**：A/B 工具只看函数，T6 才检查实际 diff 的边界与常量；两者都通过，才能说明搬移没有夹带无关改动。

## 不纳入本批

| 未纳入项 | 原因 |
| --- | --- |
| 全量回归的逐条业务断言 | 仓库 CI 的 4 个 `shards` 与聚合 job `test` 覆盖；本清单只覆盖本批调用链 |
| escalation／conflict 分支的新增业务用例 | 函数体 AST 与源码文本相同，T0 核对注入对象，现有 T4 覆盖 7 条路径；新增用例会扩大本批范围 |
| 动态重绑定 6 个注入名的场景 | 仓库内没有这类调用；本批把“导入时快照”写成冻结的内部约定，见执行计划的影响分析 |
| 性能、并发、缓存命中率 | 本批只搬移函数，没有新增 I/O 或并发路径 |
| 历史批次已覆盖的迁移、stage1 三件套 | 不属于本次 3 个函数的调用链 |

## 修订记录

| 版本 | 日期 | 说明 |
| --- | --- | --- |
| 第 1 版 | 2026-10-21 | 初稿：8 步、T0–T6、23 条 A/B 计数 |
| 第 2 版 | 2026-10-21 | 按第 1 版审核意见 T1–T9 与执行计划审核 B1、B5 修订：工具文件与哈希改成断言；第 1 步补基线断言、`FunctionDef` 计数与 `PYTHONPYCACHEPREFIX`；第 3 步补 `symtable` 自由名字与源码文本/注释核对；第 4、7、8 步把写死值改成断言；第 5、6 步加 `PYTHONPYCACHEPREFIX`，第 7 步断言没有 `__pycache__`；必测表补 R 编号与计数口径；失败处理补重试上限与停止条件；行数改为观察值说明。命令块有改动，整套重跑。 |
| 第 3 版 | 2026-10-21 | 按第 2 版复核意见 N1–N3（执行计划同轮 B1–B3／N1–N4）修订：第 7 步把 `+27 −98` 与 hunk 数保留为通过条件、2085／2014／129 改成 `printf` 观察值；第 1 步加执行前缓存清理；第 3 步的源码核对口径改成“94 行非空源码去掉缩进 + 12 行注释按顺序”；重试规则限定第 2 步才删 `base/head`，并从“不重试”列表删掉“行数”；版本指针改为执行计划第 4 版，修订记录标签与执行计划统一。 |

## 审核状态

- 第 3 版：Proposed review status: pending（第 2 版复核意见 N1–N3、执行计划同轮 B1–B3／N1–N4 已修订；reviewer 已于 2026-10-21 给出 `Test plan conclusion: APPROVED`、Gate 1：PASS、Gate 2：PASS，正式结论见其 Review record）。
- 对应执行计划：[implementation-plan.md](implementation-plan.md)，第 4 版。
- 复核通过后才能执行；执行结果写入独立记录，不改本计划第 3 版的命令与预期。
