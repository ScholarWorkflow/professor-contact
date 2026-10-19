# Stage 2 划分第六批：facts／gap／sidecar 数据层与两个上下文对象（测试执行记录）

## 版本与对象

- 执行计划：`plan/stage2-facts/implementation-plan.md` 第 2 版。
- 测试计划：`plan/stage2-facts/test-plan.md` 第 4 版。
- 被测提交：`1747c40`（`refactor(stage2): move the facts and context layer into a helper module`，父提交 `c557802` 为计划文档提交，其父为集成提交 `b862dfa`）。
- 对照基准：集成提交 `b862dfa`（`7a59006` 上依次并入 PR #112、#110、#111 后的树），runner 8191 行。
- 环境：macOS；`uv run --no-project python` 3.14.6；仓库既有测试夹具；未新增依赖。
- 运行目录：`/tmp/pc-stage6/`（`base/` 是 `b862dfa` 的 scripts，`official/` 是正式执行日志）；命令块从测试计划第 4 版原文抽出，放在 `/tmp/pc-blocks/blk0.sh`–`blk5.sh`。第 1 步已在干净的 `/tmp`（先 `rm -rf /tmp/pc-stage6`）上跑过，退出码 0，确认它自己会建目录。

## 结果

| 编号 | 结果 | 证据 |
| --- | --- | --- |
| T0 编译与工厂契约 | 通过 | 6 条 `T0 ... OK`：36 个 keyword-only 参数、18 个成员、18 个同名别名、两条常量别名在 `build()` 之前、模块不导入 runner／不做动态加载／不碰 `sys.path`／`sys.modules`、36 个实参与参数同名同集合且 18 个别名都在调用之后；`T0 CHECKS PASS`；`py_compile` 与 `--help` 退出码 0（`/tmp/pc-stage6/blk0.sh` 输出） |
| T1–T3 结构／AST／接口 | 通过 | 98 条 `OK`（T0 3、T1 37、T2 21、T3 37）、`ALL CHECKS PASS`、退出码 0；`--help` 与 `b862dfa` 逐字节相同（`diff -u` 无输出） |
| T2 的 docstring 核对 | 通过 | `total=18 with_doc=7 multi=5 clean_equal=7 without_doc=11 missing=0 mismatched=0`、`DOCSTRING CHECKS PASS`、退出码 0 |
| T4 facts／sidecar／gap 行为 | 通过 | 13 个方法：`Ran 13 tests in 5.432s`、`OK`，无失败、无跳过 |
| T5 复制夹具加载 | 通过 | 2 个方法：`Ran 2 tests in 1.143s`、`OK` |
| 失败注入 | 不适用 | 本批只搬移定义并把两条常量别名上移，不改事务／回滚／写入顺序／错误通道（见测试计划第 5 步） |
| 既有仓库检查（非必测） | 待跑 | 推 PR 后引用 4 个 `shards` 与聚合 `test` 的运行编号；不作为通过条件 |

## 文件与接缝

- 被测 runner：`.apm/skills/professor-contact/scripts/contact_state.py`，7630 行，sha256 `b2cbc73605957f2530801f837cc63ade7226f066cde94a801568ce4f5d6969e2`。
- 新模块：`.apm/skills/professor-contact/scripts/_stage2_facts.py`，694 行，sha256 `ac84c80c2e47a894bd9e8604d653ce5611ed6e7f9f88c898b9932709a4cd9437`。
- 代码 diff（`b862dfa` → 工作树）：runner `+72 −633`，新模块 `+694 −0`。新增侧是 `_stage2_facts` 加载块 12 行、两条常量别名 2 行、绑定块 59 行（与相邻空行合并后计 72 行）；删除侧是 18 个定义 598 行、旧位置两条别名 2 行，其余为删除后收敛掉的遗留空行。
- `git diff --ignore-blank-lines -U0` 的 hunk 正好 4 个：`@@ -219,0 +220,12 @@`（加载块）、`@@ -234,0 +247,2 @@`（两条常量别名上移）、`@@ -1216,632 +1230,59 @@`（18 个定义删除与绑定块新增）、`@@ -2012,2 +1452,0 @@`（旧位置的两条别名删除）；没有常量值、import、CLI、入口清单或其它顶层定义的改动。
- 空行处理：按 AST 行区间删除 18 个定义后留下 37 个连续空行，收敛为 2 个；runner 因此从 8191 行变为 7630 行。
- 18 个定义在模块内的 AST（忽略 docstring）与基线相同；7 个有 docstring 的定义清洗后同文（5 个多行），11 个原本没有 docstring。

## 说明与偏差

- 本批含两个类（`Stage2Context`、`Stage2PackRefineContext`），既有对比脚本与提取器只认函数，因此各加一个“支持顶层类”的版本：`compare_stage2_batch_v2.py`（94 行，sha256 `1ba8c0f49346b1fa78c34fbeec4d82cdab206ebef6cbf1b629769f9e5e4346b6`）、`extract_batch_v2.py`（134 行，sha256 `336c58e1937e7e735b1d1678a39630618ae5c6917ecc6be29b93a4b4e6f14b5b`）；两者与 v1 的差异都只有“顶层定义包含 `ClassDef`”。docstring 核对用 `check_docstrings_v3.py`（109 行，sha256 `31c8b2081c5d1f5398d197d2992084f371d978d99084207a7a9e7f2880f29d4a`），比第 3 批版本多支持类，并把“原本没有 docstring”记为信息而非失败。
- 两条常量别名上移：`SIDECAR_EXTRACTOR_VERSIONS`、`FACTS_GENERATOR_VERSIONS` 原来写在 `_stage2_preflight.build(...)` 之后（2012／2013），而 `load_sidecar`／`load_facts_sidecar` 需要它们；上移到 preflight 加载块之后即可让绑定块（1216）早于所有使用点。`_stage2_preflight.build` 的 30 个实参不包含这两个名字，上移不改变它的取值。
- 绑定块放在被删区间的起点（`save_projections` 之后），早于 `_stage2_resolve.build`（1857）等四个模块的绑定调用；18 个名字在 1216 之前的模块级引用为 0。
- 类的 `__qualname__` 会变成 `_stage2_facts.build.<locals>.Stage2Context`；仓库测试里没有 `__qualname__`／`__module__`／`pickle`／`inspect.getsource` 依赖，实测 0 处。
- 无测试跳过；没有改测试、常量值、CLI、入口清单或 Nix 布局。

## 复核入口

- T0：`/tmp/pc-stage6/blk0.sh`（6 条 `T0 ... OK`）。
- T1–T3：`/tmp/pc-stage6/blk1.sh`（`diff` 无输出 + 98 条 `OK`）。
- docstring：`/tmp/pc-stage6/blk2.sh`（`DOCSTRING CHECKS PASS`）。
- T4：`/tmp/pc-stage6/blk3.sh`（`Ran 13 tests`、`OK`）。
- T5：`/tmp/pc-stage6/blk4.sh`（`Ran 2 tests`、`OK`）。
- 基线对照（失败时才用）：`/tmp/pc-blocks/blk5.sh`（按第 4 版第 7 步抽出，含 `|| true`；已实跑一次，13 个方法 `OK`、退出码 0，日志 `official/baseline.log`）。
