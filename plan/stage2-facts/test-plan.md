# Stage 2 划分第六批：facts／gap／sidecar 数据层与两个上下文对象（测试计划）

## 版本、来源与状态

- 对应执行计划：[implementation-plan.md](implementation-plan.md)，计划第 2 版（`Plan conclusion: APPROVED`）。
- Requirement revision: 第 1 版（2026-10-20 负责人要求）。
- Target repository revision: 工作分支 `refactor-stage2-context`；对照基准为父分支 `refactor-stage2-resolve-commit` 的 head `3da3d4a6257f86f08426776a77246e9c687443d2`（分支链 #108 → #109 → #110 → #111 → #112 → 本批）。
- Test plan revision: 第 5 版。
- Proposed review status: **第一关 PASS、第二关 PASS**（2026-10-20）；第 5 版只把对照基准换成分支链上的父提交，判据与步骤不变。
- 测试范围依据：`Test Engineer Rule.md`。本清单是验收上限，只覆盖本批明确要达到的目标与本次直接改变的行为。

## 必测清单

| 编号 | 业务目标 | 输入 / 场景 | 预期结果 | 检查方式 |
| --- | --- | --- | --- | --- |
| T0 | 模块可编译、可加载，工厂契约完整（R1、R3、R4） | 工作树 `scripts/contact_state.py`、`scripts/_stage2_facts.py` | 两文件 `py_compile` 成功；`contact_state.py --help` 退出码 0 且输出与基线逐字节相同；`build()` 的 keyword-only 参数**精确等于** 36 个名字集合；返回 18 个成员；runner 有 18 个 `X = _stage2_facts.X` 别名且去重后仍 18 个；两条常量别名（`SIDECAR_EXTRACTOR_VERSIONS`、`FACTS_GENERATOR_VERSIONS`）出现在 `build()` 调用之前；模块不导入 runner、不做动态加载、不碰 `sys.path`／`sys.modules`；`build()` 调用的 36 个实参与参数同名同集合、18 个别名都在调用之后 | 第 1 步命令（6 条 `T0 ... OK` 与 `T0 CHECKS PASS`）；`--help` 的逐字节比较用第 2 步的 `diff -u` |
| T1 | 18 个定义确实离开 runner 顶层、进入模块 `build()`（R1） | 对照基准（`git archive b862dfa` 取出的 `scripts`）与工作树 `scripts` | `T0`：base 与 head 是两个不同目录、base 仍定义 18 个定义、head 一个都不定义；`T1`：模块存在；18 个定义逐个“runner 顶层已无 / 模块 `build()` 内有” | 第 2 步对比脚本的 `T0 ...`／`T1 ...` 行，共 40 条 `OK` |
| T2 | 搬移没有改变任何逻辑（R2） | 同上两侧源码 | 18 个定义的代码 AST 与基准完全相同（脚本忽略 docstring 内容）；docstring 单独核对：7 个有 docstring 的定义清洗后与基准同文（其中 5 个多行）、11 个原本没有 docstring；runner 其余顶层定义 AST 不变；离开 runner 的定义正好是这 18 个、没有新增；18 个定义在 runner 都有别名 | 同一脚本的 `T2 ...` 行（21 条 `OK`）；docstring 用第 2 步的 `check_docstrings_v3.py`，末行 `total=18 with_doc=7 multi=5 clean_equal=7 without_doc=11 missing=0 mismatched=0` 与 `DOCSTRING CHECKS PASS` |
| T3 | 旧接口与加载方式不变（R3、R4） | 同一进程内分别按文件路径加载两侧 runner；再以子进程直接执行改动后的 runner | 18 个名字在两侧都可调用、`inspect.signature` 字符串相同；直接执行 `contact_state.py --help` 退出码 0；模块不导入 runner、不做动态加载、不碰 `sys.path`／`sys.modules`；`build()` 的 36 个实参与参数同名同集合、18 个别名都在调用之后 | 同一脚本的 `T3 ...` 行（37 条 `OK`）与第 1 步的源码约束核对；合计 98 条 `OK`、末尾 `ALL CHECKS PASS` |
| T4 | facts／sidecar／gap 数据层与两个上下文对象的行为不变（R2） | 13 个既有方法：`test_stage2_facts_sidecar.FactsSidecarTests` 的 12 个方法；`test_contact_state.TestRunnerBasics.test_02_freshness_cache_partial_invalidation` | **条件式通过条件**：13 个方法全部 `ok` 则 T4 通过；若有失败，按第 7 步的基线对照归因——在 `b862dfa` 上跑同一组方法，基线上同样失败才记既有失败，基线通过而工作树失败记本批回归 | 第 3 步命令；`Ran 13 tests`、`OK`，无 skip／`FAIL`／`ERROR` |
| T5 | 复制 runner 的既有夹具仍能加载新模块（R4） | `test_stage5_immutable.TestWrapperKeepsInstalledLayoutLocator.test_finalize_through_wrapper_certifies_installed_layout_checker`、`test_stage5_dualtarget_contract.InstalledSharedSkillsLocatorTests.test_installed_shared_skills_layout_locator_finds_sibling` | 复制布局包含 `_stage2_facts.py`，复制后的 runner 能按路径加载它；两方法 `OK` | 第 4 步命令；`Ran 2 tests`、`OK` |

**既有仓库检查（不属于本批业务必测清单）**：仓库 CI 的 4 个 `shards` 与聚合 job `test` 照常执行，结果按运行编号与 head 单独引用；本批不因此扩张或缩减必测清单，也不在本地重跑全量套件。

## 执行步骤

准备与执行都在工作树 `/Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage2-context` 内进行；临时脚本与运行产物放仓库外 `/tmp` 目录。

1. T0：编译、直接执行、工厂契约与别名顺序（同一命令块，`set -e`）。该块放在 0 缩进，`<<'PY'` 的结束行可按原样执行。
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage2-context
RUN=/tmp/pc-stage6
mkdir -p "$RUN"
uv run --no-project python --version
uv run --no-project python -m py_compile \
  .apm/skills/professor-contact/scripts/contact_state.py \
  .apm/skills/professor-contact/scripts/_stage2_facts.py
uv run --no-project python .apm/skills/professor-contact/scripts/contact_state.py --help >"$RUN/help-head.txt"
uv run --no-project python - <<'PY'
import ast, subprocess, sys
from pathlib import Path

scripts = Path(".apm/skills/professor-contact/scripts")
runner = ast.parse((scripts / "contact_state.py").read_text())
module = ast.parse((scripts / "_stage2_facts.py").read_text())

build = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == "build")
args = {a.arg for a in build.args.kwonlyargs}
expected = {
    "atomic_json", "fail", "SCHEMA", "MANAGED_BY", "INPUT_PACK", "FRESHNESS_CACHE",
    "GAP_SCOPES", "FRESHNESS_SCOPES", "GAP_STATUSES", "AUTHORSHIP_RANK", "FACTS_SCHEMA",
    "FACTS_KIND", "FACTS_TEXT_FIELDS", "FACTS_LIST_FIELDS", "SHORTLIST_MAX",
    "SHORTLIST_FLOOR", "EXT_EVIDENCE_RE", "PLACEHOLDER_RE", "SIDECAR_EXTRACTOR_VERSIONS",
    "FACTS_GENERATOR_VERSIONS", "sha256_bytes", "quote_id", "read_json_file", "text_tokens",
    "title_tokens", "direction_machine_id", "facts_direction_id", "pack_paper_index",
    "load_input_pack", "paper_digest", "sidecar_sha", "gap_fingerprint",
    "candidate_fingerprint", "direction_relevant_keys", "pack_direction_relevant_keys",
    "direction_fingerprint",
}
assert len(expected) == 36, len(expected)
assert args == expected, (sorted(args), sorted(expected - args), sorted(args - expected))
print("T0 build has exactly the 36 keyword-only parameters OK")

returned = next(n for n in ast.walk(build) if isinstance(n, ast.Return)
                and isinstance(n.value, ast.Call))
assert len(returned.value.keywords) == 18, len(returned.value.keywords)
print("T0 build returns 18 members OK")

aliases = [n for n in runner.body if isinstance(n, ast.Assign)
           and isinstance(n.targets[0], ast.Name)
           and ast.unparse(n.value).startswith("_stage2_facts.")]
assert len(aliases) == 18, len(aliases)
assert len({n.targets[0].id for n in aliases}) == 18
assert all(ast.unparse(n.value) == "_stage2_facts." + n.targets[0].id for n in aliases)
print("T0 runner has 18 same-name module aliases OK")

call = next(n for n in runner.body if isinstance(n, ast.Assign)
            and isinstance(n.value, ast.Call) and ast.unparse(n.value.func) == "_stage2_facts_module.build")
lines = {n.targets[0].id: n.lineno for n in runner.body if isinstance(n, ast.Assign)
         and isinstance(n.targets[0], ast.Name)}
for constant in ("SIDECAR_EXTRACTOR_VERSIONS", "FACTS_GENERATOR_VERSIONS"):
    assert lines[constant] < call.lineno, (constant, lines[constant], call.lineno)
print("T0 moved constant aliases precede the factory call OK")

imported = {a.name for n in module.body if isinstance(n, ast.Import) for a in n.names}
imported |= {n.module or "" for n in module.body if isinstance(n, ast.ImportFrom)}
assert not any("contact_state" in name for name in imported), sorted(imported)
dotted = {ast.unparse(n) for n in ast.walk(module) if isinstance(n, ast.Attribute)}
assert not (dotted & {"sys.path", "sys.modules"}), sorted(dotted & {"sys.path", "sys.modules"})
dynamic = {"spec_from_file_location", "module_from_spec", "exec_module", "import_module"}
assert not {d for d in dotted if d.split(".")[-1] in dynamic}, sorted(dotted)
print("T0 module imports no runner, loads nothing dynamically, touches no sys.path/sys.modules OK")

injected = [k.arg for k in call.value.keywords]
assert sorted(injected) == sorted(expected), (len(injected), len(expected))
assert all(alias.lineno > call.end_lineno for alias in aliases)
print("T0 runner injects the same 36 names and puts all 18 aliases after the call OK")
print("T0 CHECKS PASS")
PY
```
预期：`py_compile` 与 `--help` 无输出、退出码 0；脚本打印 6 条 `T0 ... OK` 与 `T0 CHECKS PASS`。`--help` 与基线的逐字节比较在第 2 步做。

2. T1–T3：取出对照基准并运行对比脚本（`RUN` 在同一 shell 进程内使用）：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage2-context
RUN=/tmp/pc-stage6
mkdir -p "$RUN/base"
git archive 3da3d4a6257f86f08426776a77246e9c687443d2 .apm/skills/professor-contact/scripts | tar -x -C "$RUN/base"
uv run --no-project python "$RUN/base/.apm/skills/professor-contact/scripts/contact_state.py" --help > /tmp/pc-stage6/help-base.txt
diff -u /tmp/pc-stage6/help-base.txt /tmp/pc-stage6/help-head.txt
shasum -a 256 /tmp/pc-stage2-tools/compare_stage2_batch_v2.py
uv run --no-project /tmp/pc-stage2-tools/compare_stage2_batch_v2.py \
  "$RUN/base/.apm/skills/professor-contact/scripts" \
  .apm/skills/professor-contact/scripts \
  _stage2_facts _stage2_facts \
  sidecar_analysis_matches sidecar_path_matches load_sidecar load_facts_sidecar \
  compute_version_families score_gap rank_gaps shortlist_size is_later_or_same_unknown \
  gap_related freshness_candidates load_freshness_cache save_freshness_cache gap_scope_keys \
  load_papers_with_digests build_gap_pool Stage2Context Stage2PackRefineContext
```
脚本来源 `/tmp/pc-stage2-tools/compare_stage2_batch_v2.py`，94 行，sha256 `1ba8c0f49346b1fa78c34fbeec4d82cdab206ebef6cbf1b629769f9e5e4346b6`（与第 1–5 批的 `compare_stage2_batch.py` 只差“顶层定义包含类”这一处，判据与标签不变）；缺失或哈希不同时停止，不重写脚本。
预期：`diff` 无输出（`--help` 逐字节相同）；98 条 `OK`（`T0` 3、`T1` 37、`T2` 21、`T3` 37），末尾 `ALL CHECKS PASS`，退出码 0。

   随后做 docstring 核对（第 2 步的第二段，复用同一份两侧源码）：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage2-context
shasum -a 256 /tmp/pc-stage2-tools/check_docstrings_v3.py
uv run --no-project /tmp/pc-stage2-tools/check_docstrings_v3.py \
  /tmp/pc-stage6/base/.apm/skills/professor-contact/scripts \
  .apm/skills/professor-contact/scripts \
  contact_state.py _stage2_facts.py \
  sidecar_analysis_matches sidecar_path_matches load_sidecar load_facts_sidecar \
  compute_version_families score_gap rank_gaps shortlist_size is_later_or_same_unknown \
  gap_related freshness_candidates load_freshness_cache save_freshness_cache gap_scope_keys \
  load_papers_with_digests build_gap_pool Stage2Context Stage2PackRefineContext
```
   脚本 `/tmp/pc-stage2-tools/check_docstrings_v3.py`，109 行，sha256 `31c8b2081c5d1f5398d197d2992084f371d978d99084207a7a9e7f2880f29d4a`（比第 3 批用的 `check_docstrings.py` 多支持类，并把“原本没有 docstring”记为信息而不是失败）。
   预期：`total=18 with_doc=7 multi=5 clean_equal=7 without_doc=11 missing=0 mismatched=0` 与 `DOCSTRING CHECKS PASS`，退出码 0。

3. T4：只跑清单列出的 13 个方法：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage2-context/.apm/skills/professor-contact/tests
uv run --no-project python -m unittest \
  test_stage2_facts_sidecar.FactsSidecarTests.test_valid_facts_sidecar_is_normalized_into_the_pack \
  test_stage2_facts_sidecar.FactsSidecarTests.test_legacy_absolute_path_sidecar_still_accepted \
  test_stage2_facts_sidecar.FactsSidecarTests.test_sidecar_bound_to_different_analysis_is_rejected \
  test_stage2_facts_sidecar.FactsSidecarTests.test_facts_sidecar_bound_to_different_analysis_is_rejected \
  test_stage2_facts_sidecar.FactsSidecarTests.test_same_basename_sidecar_from_wrong_directory_is_rejected \
  test_stage2_facts_sidecar.FactsSidecarTests.test_facts_sidecar_from_wrong_directory_is_rejected \
  test_stage2_facts_sidecar.FactsSidecarTests.test_source_fingerprint_mismatch_fails_closed \
  test_stage2_facts_sidecar.FactsSidecarTests.test_missing_current_pdf_fails_closed \
  test_stage2_facts_sidecar.FactsSidecarTests.test_future_work_join_mismatch_fails_closed \
  test_stage2_facts_sidecar.FactsSidecarTests.test_broken_authoritative_sidecar_fails_facts_too \
  test_stage2_facts_sidecar.FactsSidecarTests.test_facts_sidecar_change_invalidates_direction_reuse \
  test_stage2_facts_sidecar.FactsSidecarTests.test_invalid_facts_sidecar_shape_fails_closed \
  test_contact_state.TestRunnerBasics.test_02_freshness_cache_partial_invalidation \
  -v
```
预期：`Ran 13 tests`、全部 `ok`；无 `skipped`／`FAIL`／`ERROR`。

4. T5：只跑清单列出的 2 个夹具方法：
```sh
set -e
cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage2-context/.apm/skills/professor-contact/tests
uv run --no-project python -m unittest \
  test_stage5_immutable.TestWrapperKeepsInstalledLayoutLocator.test_finalize_through_wrapper_certifies_installed_layout_checker \
  test_stage5_dualtarget_contract.InstalledSharedSkillsLocatorTests.test_installed_shared_skills_layout_locator_finds_sibling \
  -v
```
预期：`Ran 2 tests`、全部 `ok`。

5. 失败注入：本批不适用。本批只搬移定义与调整两条常量别名的位置，不修改事务、回滚、写入顺序或错误通道实现；必测清单里没有失败注入项，也不新增注入点。


6. 既有仓库检查（不属于本批必测项）：PR 推送后引用 4 个 `shards` 与聚合 job `test` 的运行编号与结论；不作为通过条件。

7. 失败处理：T4／T5 有失败时，先按本批回归排查，在父分支 head `3da3d4a` 上跑同一组方法：
```sh
set -e
BASELINE=/tmp/pc-stage6/base-b862dfa
rm -rf "$BASELINE"
mkdir -p "$BASELINE"
git -C /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-stage2-context archive 3da3d4a6257f86f08426776a77246e9c687443d2 | tar -x -C "$BASELINE"
cd "$BASELINE/.apm/skills/professor-contact/tests"
uv run --no-project python -m unittest \
  test_stage2_facts_sidecar.FactsSidecarTests.test_valid_facts_sidecar_is_normalized_into_the_pack \
  test_stage2_facts_sidecar.FactsSidecarTests.test_legacy_absolute_path_sidecar_still_accepted \
  test_stage2_facts_sidecar.FactsSidecarTests.test_sidecar_bound_to_different_analysis_is_rejected \
  test_stage2_facts_sidecar.FactsSidecarTests.test_facts_sidecar_bound_to_different_analysis_is_rejected \
  test_stage2_facts_sidecar.FactsSidecarTests.test_same_basename_sidecar_from_wrong_directory_is_rejected \
  test_stage2_facts_sidecar.FactsSidecarTests.test_facts_sidecar_from_wrong_directory_is_rejected \
  test_stage2_facts_sidecar.FactsSidecarTests.test_source_fingerprint_mismatch_fails_closed \
  test_stage2_facts_sidecar.FactsSidecarTests.test_missing_current_pdf_fails_closed \
  test_stage2_facts_sidecar.FactsSidecarTests.test_future_work_join_mismatch_fails_closed \
  test_stage2_facts_sidecar.FactsSidecarTests.test_broken_authoritative_sidecar_fails_facts_too \
  test_stage2_facts_sidecar.FactsSidecarTests.test_facts_sidecar_change_invalidates_direction_reuse \
  test_stage2_facts_sidecar.FactsSidecarTests.test_invalid_facts_sidecar_shape_fails_closed \
  test_contact_state.TestRunnerBasics.test_02_freshness_cache_partial_invalidation \
  -v > /tmp/pc-stage6/t4-baseline.log 2>&1 || true
cat /tmp/pc-stage6/t4-baseline.log
```
判据：基线同样失败＝既有失败；基线通过而工作树失败＝本批回归。

## 不纳入本清单的范围

| 未纳入项 | 原因 |
| --- | --- |
| 渲染／校验层与 `render_analysis_md` | 属下一批 |
| 方向解析 helper | 属后续批次 |
| 全量套件的本地重跑 | 仓库 CI 已分片执行，不作为本批必测 |
| 新模块单独的可导入性单测 | T0 的直接执行、T3 的按路径加载与 T5 的两条复制加载路径已覆盖真实加载方式 |

## 修订记录

- 第 1 版：首次提交：T0（编译／工厂契约）、T1–T3（A/B 脚本，98 条 OK）、T2 的 docstring 核对、T4（13 个方法）、T5（2 个夹具方法）。
- 第 2 版：按第一关意见修正 4 点——F1 第 7 步的基线对照改为原样跑完 13 个方法；F2 第 2 步补基线的 `--help` 与 `diff -u`（逐字节比较），T0 预期同步写明；F3 新增第 5 步“失败注入：本批不适用”及理由，后续步骤顺延；F4 第 1 步补动态加载断言与“36 个实参同名同集合、18 个别名在调用之后”的断言，T0 输出由 5 条变 6 条。同时把对比脚本与 docstring 脚本换成支持类的 v2／v3 版本，并写明哈希。
- 第 3 版：按第一关复核修正——G1 T4 行的归因说明改为“第 7 步”；G2 第 7 步的 unittest 命令末尾加 `|| true`，让基线失败时仍能打印日志并应用判据；T0 行的检查方式补“`--help` 的逐字节比较用第 2 步的 `diff -u`”。
- 第 4 版：按第二关复核修正 H1：第 1 步在 `cd` 之后加 `RUN=/tmp/pc-stage6` 与 `mkdir -p "$RUN"`，`--help` 的输出改写 `"$RUN/help-head.txt"`，这样干净机器上也能直接执行。

## 审核状态

- 第 1 版：第一关 NEEDS_MODIFICATION（F1 基线对照只覆盖 2/13；F2 `--help` 逐字节相同缺命令；F3 未标失败注入；F4 T3 的源码承诺未落地）。
- 第 2 版：第一关 NEEDS_MODIFICATION（G1 T4 行仍写“第 6 步”；G2 第 7 步在 `set -e` 下基线失败会提前退出）。
- 第 3 版：第一关 PASS；第二关 NEEDS_MODIFICATION（H1 第 1 步在干净 `/tmp` 下不可执行；H2 执行记录引用的 `blk5.sh` 是旧副本）。
- 第 5 版：把本批挂到 PR 分支链上——对照基准由集成提交 `b862dfa` 改为父分支 head `3da3d4a`，`git archive` 与失败处理命令同步；A/B、T4、T5、docstring 在新基准上重跑。
- 第 4 版：第二关 PASS（已按 H1／H2／H3 修正：第 1 步加 `RUN=/tmp/pc-stage6; mkdir -p "$RUN"` 并把 `help-head.txt` 写到 `$RUN` 下；执行记录改为引用按第 4 版第 7 步重新抽出的 `/tmp/pc-blocks/blk5.sh`）。
