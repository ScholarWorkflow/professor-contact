# 校验链三函数划分：测试执行记录（2026-10-21）

## 环境与来源

- Test plan: [test-plan.md](test-plan.md)，第 3 版（`sha256 b96123995a68ba27a467ff763892d601bc4db2792d39df8150a003ffbf6c8941`）。第 2 版按第 1 版审核意见修订后跑过一次；第 3 版又按第 2 版复核意见 N1–N3 把行数改成观察值、补了执行前缓存清理、收紧了源码核对口径，命令块有改动，整套重跑；本记录对应这次第 3 版重跑。此后测试计划只改了重试措辞与版本指针（`e704ea69…` → `fe9eadf5…`），8 个命令块逐字节未变，抽块与执行脚本相同，结果复用。
- 执行命令来源：把 test-plan.md 的 8 个 `sh` 代码块按顺序抽成脚本 `/tmp/pc-stage21/run-test-plan-v5.sh`（`sha256 a0437ef6737660ae4acdf098fcaa66a07a8da7d7e016ea2cd09402aefeccd031`），逐字执行；执行结束再抽一次，与执行用的脚本逐字节相同（`identical: True`）。
- 解释器：`uv run --no-project python`，Python 3.14.6（CI 为 3.12）。
- 基线：工作树 `HEAD` = `58c71c02cd0b6d66aae4cda5b7cc815431a461e6`（第 20 批 head），与测试计划写死的 `EXPECTED_BASE` 相同。
- 分支基点：执行时分支父提交是 `58c71c02…`；PR #126／#127 合并后本分支 rebase 到 `origin/main` 的 `fec405b`，`fec405b` 的 `contact_state.py` 与 `58c71c02…` 逐字节相同，本记录的全部测量与 hunk 仍对应同一份代码。
- 工作树：`/Users/rekidunois/code/skill-repos-dev/worktrees/refactor-verify-chain`；执行时改动尚未提交，`git status --porcelain` 恰好 3 条。
- 整份脚本退出码：`0`。
- 缓存：第 1 步先 `rm -rf scripts/__pycache__ tests/__pycache__` 清掉旧缓存，之后各步设 `PYTHONPYCACHEPREFIX=/tmp/pc-stage21/pycache`；执行后 `scripts/` 与 `tests/` 下没有 `__pycache__`。

## 结果

| 编号 | 命令要点 | 实测输出 | 结论 |
| --- | --- | --- | --- |
| T0 | 基线断言、`py_compile`、工厂契约、绑定位置、加载约束、`FunctionDef` 计数 | `T0 CHECKS PASS`；`--help` 退出码 0 | 通过 |
| T1 | A/B 脚本 T0／T1 段 | 10 条 `OK`（T0 3、T1 7） | 通过 |
| T2 | A/B 脚本 T2 段 + docstring 工具 + `symtable` + 源码文本核对 | 6 条 `OK`；`total=3 with_doc=1 multi=0 clean_equal=1 without_doc=2 missing=0 mismatched=0`、`DOCSTRING CHECKS PASS`、`FREE NAMES OK`、`SOURCE TEXT IDENTICAL (94 lines, 12 comments)` | 通过 |
| T3 | A/B 脚本 T3 段 + 两个 runner 的 `--help` 比对 | 7 条 `OK`；`ALL CHECKS PASS`（整份 23 条 `OK`）；`cmp` 无输出、3221 字节、sha256 `d622b7e6…` | 通过 |
| T4 | 3 个校验缓存契约方法（真实 CLI 子进程） | `Ran 3 tests in 1.362s`、`OK` | 通过 |
| T5 | 安装布局 wrapper 的既有方法 | `Ran 1 test in 0.768s`、`OK` | 通过 |
| T6 | 接缝、常量值与尺寸 | `git status --porcelain` 3 条：`M contact_state.py`、`?? _verify_chain.py`、`?? plan/verify-chain/`；无 `__pycache__`；`git diff --stat`：`1 file changed, 27 insertions(+), 98 deletions(-)`；`-U0` hunk 2 个、默认上下文 2 个（`@@ -1200,98 +1200,11 @@`、`@@ -1386,0 +1300,16 @@`）；行数观察值 2085、2014、129；顶层字面量赋值 67 个，与父提交同名同值（`CONSTANTS UNCHANGED (67)`） | 通过 |

第 8 步同时记下本批两个文件的摘要：`contact_state.py` 为 `acc1ab20929c25376552c7f53bd2a48b5aad4331ec32ded9ce44f9e43a6fdcbb`，`_verify_chain.py` 为 `512acbead24f4550792131ebeed9afdede6d7f734ed8db364ae5d6a201dc27ea`。两项都与测试计划第 8 步写死的值相同。

## 与第 1 版的差异

- 第 1 版命令块有三处缺陷：第 1 步用 `"sys.path" not in module_src` 判断加载路径，命中的是 docstring 文字；第 7 步 `git show "$BASE:$S"` 传的是目录，行数断言必然失败；第 7 步要求 `?? plan/verify-chain/`，但首次运行时文档还没复制进工作树。第 2 版分别改成 AST 导入集合检查、`git show "$BASE:$S/contact_state.py"`、先放文档再运行。
- 第 2 版按审核意见补了：工具文件与哈希断言、第 1 步基线断言与 `FunctionDef` 计数、`symtable` 自由名字检查、源码文本与 12 行注释核对、第 4／7／8 步把写死值改成断言、`PYTHONPYCACHEPREFIX` 与无 `__pycache__` 断言、失败处理的重试上限与停止条件。
- 第 3 版按复核意见把 `+27 −98` 与 hunk 数保留为通过条件、行数改成 `printf` 观察值，第 1 步加执行前缓存清理，源码核对口径写成“94 行非空源码去掉缩进 + 12 行注释按顺序”，重试规则限定第 2 步才删 `base/head`。
- 代码侧同时把模块 docstring 首行与 runner 加载块首行从 `Stage-2` 改成 `Verify-chain`（只改注释与 docstring 文案，不改函数体）；因此两个文件的 sha256 由 `dd762c79…`／`23e962c7…` 变为 `acc1ab20…`／`512acbea…`，第 8 步的断言按新值写。

## 覆盖说明（按命令分发路径，不是调用计数）

T4 的 3 个方法都从 CLI 子进程进入 `stage5-plan`，命令分发把它们接到校验缓存路径：`verify_state` 读取 `_contact_verify.json`（`read_json_file`），用 `current_source_fingerprints` 计算指纹，命中时按 `VERIFY_TTL_DAYS`、`VERIFY_TIMESTAMP_FORMAT` 判定新鲜度；`test_b` 的 4 个 subTest 覆盖时间戳、天数、来源指纹的格式不兼容分支，`test_c` 覆盖 mtime 漂移与 31 天过期两条拒绝路径。`email_item_is_evidence_seeded` 只在 `decision.status` 为 `escalate` 或 `needs_refresh` 的分支调用，本批 7 条路径没有触发；它的未变由 T0 的对象同一性与 R2 的 AST／源码文本核对保证，不由 T4 覆盖。T5 从安装布局的 wrapper 进入 finalize，仍能定位并执行 `contact_state.py`，验证按路径加载新模块不依赖当前目录。

## 未执行或未通过的项

- 无跳过的必测项。
- 仓库 CI（4 个 `shards` + 聚合 job `test`）按测试计划属既有检查，不在本记录内，推送后在 PR 上核对。

## 结论

T0–T6 全部按第 3 版测试计划执行并通过，没有修改输入或预期求通过；修正的检查都只是把断言改准（AST 代替子串、补全文件路径、先把文档放进工作树、工具与摘要改成断言），判定口径没有放宽。代码侧的文案改动只影响注释与 docstring，AST 相等、源码文本（含 12 行注释）与 `--help` 都证明行为未变。
