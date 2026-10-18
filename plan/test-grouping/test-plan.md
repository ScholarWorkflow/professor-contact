# 测试分组与 CI 分片（测试计划）

## 版本、来源与状态

- 对应执行计划：[implementation-plan.md](implementation-plan.md)，计划第 2 版（`Plan conclusion: APPROVED`）。
- 需求来源：负责人 2026-10-18“其余边界”中的“测试分组／CI：可以另评估快审，但不能只按 test_stageN 文件名筛选”。
- 对照基准与目标修订：`6e624e0`（`origin/main`）；本批工作分支 `refactor-test-grouping`。
- Test plan revision: 第 3 版。
- 测试范围依据：`Test Engineer Rule.md`；提交前按共用清单 `plan/test-plan-checklist.md` 自检（该清单随 PR #98 引入，本分支从 `main` 拉出、不把它当作已存在的文件；自检小节已逐条写明）。
- Proposed review status: pending。

## 必测清单

| 编号 | 业务目标 | 输入 / 场景 | 预期结果 | 检查方式 |
| --- | --- | --- | --- | --- |
| T1 | 覆盖校验能挡住“漏归类／重复／不存在／空分片”，并接受正确清单 | 正确清单；四种坏清单：① 从某片删掉一个模块；② 把某模块同时放进两片；③ 某片加一个不存在的模块名；④ 把某片的模块列表置空 | 正确清单退出码 0 且 stdout 含 `OK: 78 test modules across 4 shards`；四种坏清单都非零退出，且 stderr **分别**含 `not covered by any shard`／`listed in both`／`no such test module`／`lists no modules`；每次注入后恢复清单并复跑通过 | 仓库根 `python scripts/check_test_shards.py`；注入用带 `try/finally` 的片段临时改写 `plan/test-grouping/shards.json` 并在结束时恢复，最后用 `git diff --exit-code` 确认清单回到原样；**逐例断言对应错误子串**，不只比退出码 |
| T2 | 四个分片的并集等于全套、且各自通过 | 四片各自的模块列表 | 四片都 `OK`；四片 `Ran N tests` 之和 = `unittest` 收集数（1025）；无重复执行 | `python scripts/check_test_shards.py --print <shard>` 取列表，在 `tests/` 目录逐片 `python -m unittest <列表>` |
| T3 | 工作流结构保持单一 `test` 门禁 | `.github/workflows/ci.yml` | `shards` 任务为 4 组合 matrix、`fail-fast: false`、每片先跑覆盖校验再跑本片；`test` 聚合任务 `needs: [shards]`、`if: always()`、`needs.shards.result != success` 即失败 | 读取工作流文本逐条核对；CI 跑起来后核对检查项名（`shards (shardN)` 与 `test`） |
| T4 | 每个分片命令可独立在本地执行 | 四片的命令（从 `tests/` 目录） | 都能独立跑通，不依赖其它分片产生的文件 | 同 T2 |
| T5 | 既有仓库检查 | 仓库 CI 在本 PR 上的运行 | 4 个 `shards (shardN)` 与聚合 `test` 全部成功 | 引用 PR 检查项（运行编号、所跑 head、各检查状态），不作为本批业务必测项 |

## 执行步骤

准备与执行都在工作树 `/Users/rekidunois/code/skill-repos-dev/worktrees/refactor-test-grouping` 内进行（本批不需要仓库外临时脚本；所有脚本都在仓库内）。

1. 准备：确认工作树只有本批改动、Python 可用，并记录被测提交。
   ```sh
   set -e
   cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-test-grouping
   git status --porcelain
   python3 --version
   git rev-parse --short HEAD
   ```
2. T1：正确清单 + 四种坏清单。注入用一次性 Python 片段改写 `shards.json`，每次注入后**必须恢复**并用 `git diff --exit-code` 确认清单与提交一致。
   ```sh
   set -e
   python3 scripts/check_test_shards.py
   # 注入与恢复（四种坏清单各一次）
   python3 - <<'PY'
   import json, subprocess, sys
   from pathlib import Path
   manifest = Path("plan/test-grouping/shards.json")
   backup = manifest.read_text(encoding="utf-8")
   def check():
       proc = subprocess.run([sys.executable, "scripts/check_test_shards.py"],
                             capture_output=True, text=True)
       return proc.returncode, proc.stdout, proc.stderr
   code, out, _ = check()
   assert code == 0 and "OK: 78 test modules across 4 shards" in out
   cases = {
       "missing": ("not covered by any shard", lambda d: d["shards"][0]["modules"].pop(0)),
       "duplicate": ("listed in both",
                     lambda d: d["shards"][1]["modules"].append(d["shards"][0]["modules"][0])),
       "nonexistent": ("no such test module",
                       lambda d: d["shards"][2]["modules"].append("test_does_not_exist")),
       "empty_shard": ("lists no modules",
                       lambda d: d["shards"][3].__setitem__("modules", [])),
   }
   try:
       for name, (needle, mutate) in cases.items():
           broken = json.loads(backup)
           mutate(broken)
           manifest.write_text(json.dumps(broken, ensure_ascii=False), encoding="utf-8")
           code, _, err = check()
           print(name, "->", code, "|", needle in err)
           assert code != 0 and needle in err, name
   finally:
       manifest.write_text(backup, encoding="utf-8")
   assert check()[0] == 0
   PY
   git diff --exit-code -- plan/test-grouping/shards.json
   ```
   预期：正确清单退出 0 且 stdout 含 `OK: 78 test modules across 4 shards`；`missing`／`duplicate`／`nonexistent`／`empty_shard` 四次注入都非零退出且 stderr 含各自对应的错误子串（见 T1 行）；恢复后再次为 0；`git diff --exit-code` 无输出。
3. T2/T4：逐片跑并记录计数与墙钟。
   ```sh
   set -e
   cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-test-grouping
   for shard in shard1 shard2 shard3 shard4; do
     modules=$(python3 scripts/check_test_shards.py --print "$shard")
     start=$(date +%s)
     (cd .apm/skills/professor-contact/tests && python3 -m unittest $modules) | tail -3
     echo "$shard wall=$(( $(date +%s) - start ))s"
   done
   ```
   预期：四片都 `OK`；四片 `Ran N tests` 之和等于 `python3 -c "import unittest;print(unittest.TestLoader().discover('.apm/skills/professor-contact/tests', pattern='test_*.py').countTestCases())"` 的输出。
4. T3：核对工作流结构。
   ```sh
   set -e
   cd /Users/rekidunois/code/skill-repos-dev/worktrees/refactor-test-grouping
   grep -n "fail-fast\|matrix\|shard:\|needs:\|if: always\|needs.shards.result" .github/workflows/ci.yml
   ```
   预期：能看到 `fail-fast: false`、四个分片组合、每片的覆盖校验步骤、`needs: [shards]`、`if: always()` 与 `!= "success"` 判定。
5. T5：推送后引用 CI 运行（4 个分片 + 聚合 `test`），记录运行编号与所跑 head。
6. 失败处理：分片失败先看该片的日志定位模块；覆盖校验失败按 `ERROR:` 行修 `shards.json`；工作流失败区分 YAML 结构问题与测试失败。

## 环境与预检

- 本地 macOS／Python 3.14.7；CI 为 ubuntu-latest／Python 3.12，墙钟与耗时分布会不同（README 已写明首次 CI 后按实测更新）。
- 本批不接触用户业务资料；分片命令与覆盖校验都只读测试目录。

## 不纳入本清单的范围

| 未纳入项 | 原因 |
| --- | --- |
| 测试内容本身的正确性 | 本批不改测试与产品代码；分片只改变执行方式 |
| 按改动路径跳过测试 | 执行计划已列为非目标（runner 是共享核心） |
| 分支保护设置的改动 | 方案保持必需检查名为 `test`，无需改保护规则 |

## 自检

按 `plan/test-plan-checklist.md` 逐条核对：① 必测项只覆盖本批行为（校验脚本、分片并集、工作流结构）；② CI 作为既有仓库检查单独引用、不占必测编号；③ 本批没有仓库外临时脚本，注入片段就地给出且必须恢复；④ 命令块全部 `set -e`；⑤ 失败注入到达目标分支（四种坏清单各自触发对应 `ERROR:`）；⑥ 计划与记录同一套标签；⑦ 编号 T1–T5、版本指针与执行计划第 2 版一致。

## 修订记录

- 第 1 版：首次提交测试计划审核。
- 第 2 版：按第一关口的 B1 把 T1 从“只比退出码”改为**逐例断言对应错误子串**（`not covered by any shard`／`listed in both`／`no such test module`），并补第四个注入“某片模块列表置空”（`lists no modules`）；片段加 `try/finally` 保证断言失败也会恢复清单；正确清单那次同时断言 stdout 的 `OK: 78 test modules across 4 shards`。
- 第 3 版：把三处仍写“三种坏清单”的摘要改为“四种”，与 T1 行、注入片段和实测结果一致；T5 补上 PR #103 的 CI 运行编号与各检查状态。

## 审核状态

测试计划第 3 版为当前唯一版本。第 1 版第二关口 PASS、第一关口有 1 项 blocker（B1），第 2 版修正后第一、二关口 PASS；第 3 版只改摘要口径与补 T5 的 CI 来源。后续审核以本文件、执行计划与 `Test Engineer Rule.md` 为输入。
