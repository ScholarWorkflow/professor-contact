# Stage 3 划分第二批：plan／finalize／overview 命令（测试计划）

## 版本、来源与状态

- 对应执行计划：[implementation-plan.md](implementation-plan.md)，第 2 版（已取得独立执行计划审核批准）。
- Requirement revision: 第 1 版（2026-10-20 负责人要求；同一系列见 PR #95–#118）。
- Target repository revision: `refactor-stage3-commands` 的 `9dee330b38e2968f9734a870114cef2bc94e9e46`；已测试实现 `75392405815d1bf7db6af3ae866b0c8bd7879ad2` 中的 `contact_state.py`、`_stage3_commands.py` 与当前提交文件对象相同。固定测试基准为 #118 的 `e303a1c99e44d4171bd0089901f67e67b506fbc1`；其相关脚本与当前 `main` 的 #118 合并提交 `4cfcf49fe23bde455dabcb417f4cd9cd789665fd` 相同。本次计划修订不改变被测代码及业务目标。
- Test plan revision: 第 3 版（范围与失败处理修订）。
- Proposed review status: 待审核（第 3 版；历史批准仅作复用依据）。
- 测试范围依据：`Test Engineer Rule.md`。

## 必测清单

| 编号 | 业务目标 | 输入 / 场景 | 预期结果 | 检查方式 |
| --- | --- | --- | --- | --- |
| T0 | runner 与新模块可编译、可启动；工厂参数形态与禁止反向依赖符合本批约定（R3） | 当前 `scripts/contact_state.py`、`scripts/_stage3_commands.py` | 两文件编译成功，runner `--help` 退出码为 0；`build()` 有 56 个必填关键字参数，无位置参数和额外可变参数；模块不导入 runner、不动态加载程序、不操作 `sys.path`／`sys.modules`。定义搬移、别名集合和绑定先后由 T1／T3 的同一次对照检查承担，不重复作为 T0 通过条件 | 第 1 步；2 条 `T0 ... OK` 与 `T0 CHECKS PASS` |
| T1 | 4 个定义从 runner 顶层移入新模块（R1） | 固定基准脚本与当前脚本 | 基准仍在 runner 定义四个函数；当前 runner 不再定义，新模块 `build()` 内恰好包含这四个定义 | 第 2 步对比脚本的目录对照与 `T1` 分组（脚本内部仍输出 `T0` 3 条、`T1` 9 条，共 12 条 `OK`；这里的内部 `T0` 是目录对照提示，并非必测 T0 的重复运行） |
| T2 | 四个定义的原有逻辑和其他顶层定义不变（R2） | 相同的固定基准与当前源码 | 4 个函数体的抽象语法树与基准一致（忽略文档字符串），文档字符串核对一致；其余顶层定义不变，仅有这四个定义被移出 | 第 2 步对比脚本中的 `T2` 7 条 `OK` 与原有文档字符串核对，沿用既有工具 |
| T3 | 原接口、参数对应、别名绑定与帮助文本不变（R3、R4、R5） | 两侧脚本按文件路径加载；当前 runner 从命令行启动 | 两侧四个命令入口可调用且函数签名一致；56 个注入参数与实参同名；四个别名在 `canonical_professor_dir` 定义完成且绑定调用之后建立；runner 从相邻文件路径加载新模块；帮助文本与固定基准逐字节相同 | 第 2 步对比脚本的 `T3` 9 条 `OK`，以及一次 `diff -u`；对比脚本总计 28 条 `OK` 和 `ALL CHECKS PASS` |
| T4 | `stage3-plan`／`stage3-finalize`／`stage3-rebuild-overview` 及选中范围的业务行为保持一致（R2） | 第 3 步所列的 10 个既有单元测试方法，其中测试运行经真实命令行子进程 | 10 个方法全部通过可直接认定本批目标通过；若有失败，仅检查与 Stage 3 命令有关的断言及受其直接影响的行为。`test_04` 的 Stage 4、`test_05` 的 Stage 5 断言失败本身不构成本批回归；按第 5 步归因，不能判明时记为无法判断 | 第 3 步现有 10 个方法，首次结果与必要归因记录；不额外要求整个 Stage 4／5 业务通过 |
| T5 | runner 与新模块在仓库外临时复制目录中仍能一起加载（R1、R5） | 复制正式 `scripts` 到一次性隔离目录；直接从该目录运行 runner | 复制后相邻目录包含 `_stage3_commands.py`，`contact_state.py --help` 成功退出，表明模块能随 runner 一起加载。此项仅验证相邻脚本加载，不作为正式安装路径验收；第五阶段联系方式、上游证据检查均不是通过条件 | 第 4 步的临时目录加载检查，输出 `T5 COPIED LAYOUT PASS`；已有第 2 版两项夹具成功记录能证明同一目标时直接复用，无须重跑 |

**结果复用**：第 2 版在已测试代码上的 T0—T5 均已取得通过记录；第 3 版缩减重复检查和范围外断言，不改变业务预期。原记录中能直接判断本版目标的结果继续有效；没有受影响的业务项不得因提交号或计划版号变化重跑。

**既有仓库检查（不属于本批业务必测清单）**：仓库 CI 的 4 个 `shards` 与聚合 job `test` 照常执行，结果按运行编号与 head 单独引用；本批不在本地重跑全量套件。

## 执行步骤

准备与执行都在工作树 `/Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage3-commands` 内进行；临时脚本与运行产物放仓库外 `/tmp/pc-stage11`。

1. T0：只检查可编译、可启动、必填参数形态及模块的反向依赖限制；定义搬移与同名别名交给 T1／T3 一次核对。
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage3-commands
RUN=/tmp/pc-stage11
mkdir -p "$RUN"
uv run --no-project python --version
uv run --no-project python -m py_compile \
  .apm/skills/professor-contact/scripts/contact_state.py \
  .apm/skills/professor-contact/scripts/_stage3_commands.py
uv run --no-project python .apm/skills/professor-contact/scripts/contact_state.py --help >"$RUN/help-head.txt"
uv run --no-project python - <<'PY'
import ast
from pathlib import Path

scripts = Path(".apm/skills/professor-contact/scripts")
module = ast.parse((scripts / "_stage3_commands.py").read_text(encoding="utf-8"))
builds = [node for node in module.body
          if isinstance(node, ast.FunctionDef) and node.name == "build"]
assert len(builds) == 1
args = builds[0].args
assert len(args.kwonlyargs) == 56
assert not args.args and not args.posonlyargs and not args.vararg and not args.kwarg
assert all(default is None for default in args.kw_defaults)
print("T0 build has 56 required keyword-only inputs OK")

imported = {a.name for n in module.body if isinstance(n, ast.Import) for a in n.names}
imported |= {n.module or "" for n in module.body if isinstance(n, ast.ImportFrom)}
from_names = {a.name for n in module.body if isinstance(n, ast.ImportFrom) for a in n.names}
assert not any("contact_state" in name for name in imported)
assert not any("contact_state" in name for name in from_names)
dotted = {ast.unparse(n) for n in ast.walk(module) if isinstance(n, ast.Attribute)}
assert not (dotted & {"sys.path", "sys.modules"})
dynamic = {"spec_from_file_location", "module_from_spec", "exec_module", "import_module"}
assert not {d for d in dotted if d.split(".")[-1] in dynamic}
assert not (from_names & dynamic)
names_used = {n.id for n in ast.walk(module) if isinstance(n, ast.Name)}
assert not (names_used & {"__import__", "exec", "eval"})
print("T0 module has no runner import, dynamic loading or sys.path/sys.modules changes OK")
print("T0 CHECKS PASS")
PY
```
预期：编译和帮助命令退出码为 0；内嵌脚本打印两条 `T0 ... OK` 与 `T0 CHECKS PASS`。首次执行时保存输出到 `/tmp/pc-stage11/t0.log`，如 `bash blk0.sh > /tmp/pc-stage11/t0.log 2>&1`；已有效的第 2 版 T0 结果可直接沿用，不要求为缩减后的断言重新执行。

2. T1–T3：取出对照基准、比对 `--help`、运行对比脚本与 docstring 核对：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage3-commands
RUN=/tmp/pc-stage11
rm -rf "$RUN/base"
mkdir -p "$RUN/base"
BASE_SHA=e303a1c99e44d4171bd0089901f67e67b506fbc1
git archive "$BASE_SHA" .apm/skills/professor-contact/scripts | tar -x -C "$RUN/base"
uv run --no-project python "$RUN/base/.apm/skills/professor-contact/scripts/contact_state.py" --help >"$RUN/help-base.txt"
diff -u "$RUN/help-base.txt" "$RUN/help-head.txt"
shasum -a 256 /tmp/pc-stage2-tools/compare_stage2_batch_v2.py
uv run --no-project /tmp/pc-stage2-tools/compare_stage2_batch_v2.py \
  "$RUN/base/.apm/skills/professor-contact/scripts" \
  .apm/skills/professor-contact/scripts \
  _stage3_commands _stage3_commands \
  _stage3_selected_scope_keys cmd_stage3_plan cmd_stage3_finalize cmd_stage3_rebuild_overview
```
脚本来源 `/tmp/pc-stage2-tools/compare_stage2_batch_v2.py`，94 行，sha256 `1ba8c0f49346b1fa78c34fbeec4d82cdab206ebef6cbf1b629769f9e5e4346b6`。
预期：`diff` 无输出；28 条 `OK`（`T0` 3、`T1` 9、`T2` 7、`T3` 9），末尾 `ALL CHECKS PASS`，退出码 0。

   随后做 docstring 核对（只读，必须核对整行摘要）：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage3-commands
RUN=/tmp/pc-stage11
shasum -a 256 /tmp/pc-stage2-tools/check_docstrings_v3.py
uv run --no-project /tmp/pc-stage2-tools/check_docstrings_v3.py \
  "$RUN/base/.apm/skills/professor-contact/scripts" \
  .apm/skills/professor-contact/scripts \
  contact_state.py _stage3_commands.py \
  _stage3_selected_scope_keys cmd_stage3_plan cmd_stage3_finalize cmd_stage3_rebuild_overview
```
脚本 `/tmp/pc-stage2-tools/check_docstrings_v3.py`，109 行，sha256 `31c8b2081c5d1f5398d197d2992084f371d978d99084207a7a9e7f2880f29d4a`。
预期：整行 `total=4 with_doc=2 multi=2 clean_equal=2 without_doc=2 missing=0 mismatched=0` 与末行 `DOCSTRING CHECKS PASS`，退出码 0。

3. T4：只运行清单的 10 个既有方法，不增加 Stage 4／5 的独立测试。首次运行写入 `t4.log`；失败时保留日志并转第 5 步判断，不自动重跑。
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage3-commands/.apm/skills/professor-contact/tests
T4_LOG="${T4_LOG:-/tmp/pc-stage11/t4.log}"
uv run --no-project python -m unittest \
  test_contact_state.TestRunnerBasics.test_04_profile_change_invalidates_stage3_not_stage2 \
  test_contact_state.TestRunnerBasics.test_05_missing_packs_need_refresh \
  test_contact_state.TestRunnerBasics.test_05b_collection_key_limits_stage3 \
  test_contact_state.TestRunnerBasics.test_05c_scoped_stage3_refresh_preserves_other_state \
  test_contact_state.TestRunnerBasics.test_05d_scoped_stage3_rejects_six_generated_candidates \
  test_contact_state.TestRunnerBasics.test_05e_overview_manual_edit_does_not_block_local_finalize \
  test_contact_state.TestRunnerBasics.test_09_missing_result_keeps_state \
  test_contact_state.Issue67AdjacentStateTests.test_01_stage3_selected_refresh_scopes_from_the_professor_local_selection \
  test_contact_state.Issue67AdjacentStateTests.test_03_scoped_finalize_with_the_local_selection_keeps_other_directions \
  test_issue66_stage3_local_state.Issue66LocalStateTests.test_rebuild_overview_uses_professor_local_states_and_rebuilds_deleted_projection \
  -v > "$T4_LOG" 2>&1
cat "$T4_LOG"
```
预期：`Ran 10 tests`、10 个方法通过且无跳过。失败时不得仅凭整组退出码判定本批业务失败，须按第 5 步确认失败断言涉及的目标；已有第 2 版有效结果直接复用。

4. T5：只检查仓库外临时复制目录中的相邻脚本加载；取消原来两个第五阶段业务测试作为本批通过条件。
```sh
set -e
ROOT=/Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage3-commands
RUN=/tmp/pc-stage11
mkdir -p "$RUN"
COPYDIR=$(mktemp -d "$RUN/copy-XXXXXXXX")
trap 'rm -rf "$COPYDIR"' EXIT
T5_LOG="${T5_LOG:-$RUN/t5.log}"
{
  cp -R "$ROOT/.apm/skills/professor-contact/scripts" "$COPYDIR/scripts"
  test -f "$COPYDIR/scripts/_stage3_commands.py"
  uv run --no-project python "$COPYDIR/scripts/contact_state.py" --help >"$RUN/t5-help.txt"
  printf 'T5 COPIED LAYOUT PASS\\n'
} >"$T5_LOG" 2>&1
cat "$T5_LOG"
```
预期：输出 `T5 COPIED LAYOUT PASS`，退出码为 0；隔离目录随退出清理。此项不模拟正式安装，也不检查第五阶段业务结果。第 2 版已经通过的两项现有夹具包含复制脚本并成功导入 runner 的检查，因此其结果可用于当前 T5 的相同目标；不要求补跑本步骤。

5. 失败记录、最小对照与停止条件：

- **先保留第一次结果，禁止为取得通过而重跑。** T0—T5 发生异常时，保存首次日志及对应代码版本。若断言直接显示四个函数搬移后的业务或加载行为不符，记录业务失败；若仅是启动环境、临时依赖或无关第五阶段业务断言失败，分别记录环境受阻或范围外问题。无法归因时记录「无法判断」，不得冒充本批通过或失败。
- **必要的父提交对照**：只有 T4 失败且现有日志无法确定其是否由本批 Stage 3 改动导致时，针对实际失败的**同一个**测试方法在固定基准上运行一次。必须由执行者显式提供 `METHOD` 的完整名称，没有默认方法。两侧同一方法失败，不自动判为「既有失败」；还须核对是否是同一业务断言、同一症状以及是否由本批造成。两侧结果仍不能确定时保留「无法判断」。
- **外部故障的唯一允许重试**：仅限测试业务命令尚未开始前的外部解释器／依赖启动故障，且已用最小预检确认故障恢复；同一输入、代码、配置和隔离状态下最多重试 **1 次**。业务断言失败、已产生正式业务副作用、服务故障未恢复或观察信息仍缺失时停止，不重试。重试使用新的 `T4_LOG`／`T5_LOG` 路径（或首次日志另存后再执行），保留每次尝试的故障原因和结果，不能覆盖首次结果。测试使用独立临时目录，不接触用户或生产数据。

仅在需要 T4 父提交对照时运行以下命令；先设置为日志中**真正失败**的完整方法名：
```sh
set -eu
: "${METHOD:?必须显式设置本轮 T4 实际失败的完整 unittest 方法名}"
ROOT=/Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage3-commands
BASE_SHA=e303a1c99e44d4171bd0089901f67e67b506fbc1
BASELINE=/tmp/pc-stage11/base-${BASE_SHA:0:12}
if [ ! -d "$BASELINE/.apm/skills/professor-contact/tests" ]; then
  mkdir -p "$BASELINE"
  git -C "$ROOT" archive "$BASE_SHA" | tar -x -C "$BASELINE"
fi
LOG="$BASELINE/baseline-${METHOD##*.}-$(date +%Y%m%d-%H%M%S).log"
cd "$BASELINE/.apm/skills/professor-contact/tests"
set +e
uv run --no-project python -m unittest "$METHOD" -v >"$LOG" 2>&1
STATUS=$?
set -e
cat "$LOG"
printf 'baseline_exit_code=%s; log=%s\\n' "$STATUS" "$LOG"
```
对照只用于解释实际失败，不替代当前版本的业务结果。没有失败或已有结果足够判断时不执行本步。

6. 失败注入：本批不适用。本批只搬移定义，不改事务、回滚、写入顺序或错误通道；必测清单里没有失败注入项。

7. 既有仓库检查（不属于本批必测项，也不作为通过条件）：PR 推送后引用 4 个 `shards` 与聚合 job `test` 的运行编号与结论。

## 不纳入本清单的范围

| 未纳入项 | 原因 |
| --- | --- |
| `validate_candidate_result`／`validate_cross_result`／`render_candidates_*`／`_stage3_args_from_invocation` | 后续批次；本批按引用注入 |
| Stage 4／5 的独立业务结果与迁移命令 | 后续批次；既有测试中的相邻断言只用于判断 Stage 3 是否直接引发失败，不作为本批额外通过条件 |
| 全量套件的本地重跑 | 仓库 CI 已分片执行，不作为本批必测 |
| R6 的空行接缝 | 属实现侧核对（执行计划第 3 步的只读脚本），不单列用例 |

## 修订记录

- 第 1 版：首次提交（含演练实测的 28 条 OK、10＋2 个方法与 docstring 期望值）。
- 第 2 版：按第一关意见补 T4 失败归因、第 3／4 步输出重定向、`posonlyargs` 断言与 T5 说明；按第二关意见补 T0 的 `t0.log` 落盘说明、第 5 步 `METHOD` 必须替换为真实失败方法、T4／T5 失败时先另存日志。
- 第 3 版：删去 T0 与 T1／T3 的重复通过条件；T5 只检查复制目录中新模块的加载，移除第五阶段业务通过条件；失败对照强制填写实际方法，取消自动重跑与仅凭父分支失败判断「既有失败」；明确外部故障最多一次有条件重试和已有结果复用；同步更新执行计划与固定基准版本引用。未更改被测代码、业务目标或既有测试源码。

## 审核状态

- 第 1 版：第一关 PASS。
- 第 2 版：第二关 PASS（历史记录，适用于当时版本）。
- 第 3 版：待本轮审核。原有 PASS 不自动复制为第 3 版结论；未触及的业务结果按规则复用。
