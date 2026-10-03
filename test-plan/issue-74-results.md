# 第 74 号议题第六版测试执行与静态检查结果（执行者记录）

本记录由本地执行 agent 按第六版冻结方案（`issue74-test-r6`，提交 `3e118cf561409dcb6c40be20933d2cb4f87b3edf`）执行一次 G74 并完成 S74 后发布。按方案第 2 节，执行者保存证据，审核者判断有效性；第三关口结论与合并就绪判断归审核者，本记录不代替该判断。

## 输入与版本

- 正式需求：[第 74 号议题需求第 1 版](https://github.com/ScholarWorkflow/professor-contact/issues/74)，R1—R4，读取更新时间 `2026-10-02T16:02:24Z`。
- 执行计划：[第三版](https://github.com/ScholarWorkflow/professor-contact/blob/a328e788a21af8fc7d3ebf052c399054d242b786/plan/issue-74.md)，批准保留；r5/r6 两次 Recipe 修订均不触发计划重开。
- 测试方案：`issue74-test-r6`，提交 `3e118cf561409dcb6c40be20933d2cb4f87b3edf`。
- 产品提交：`3e118cf561409dcb6c40be20933d2cb4f87b3edf`（产品实现在 `79a0568d6b92d07d83ab20b8d7d3a66482a27619` 未变，r6 只修订方案文件）；兼容基准 `768b49ef4514e36edec6b57ed3821a99af9e9c00`。
- 判定入口：`.apm/skills/professor-contact/tests/gate2_evidence.py`，提交 `f7917830d34f7b107f757cf2b6a476cc752631ab`（与第三版官方运行一致）。
- 环境：CPython 3.12.13（`uv run --no-project --python 3.12`）、uv 0.12.11、macOS。

## 第五版运行的位置绑定失败（重开依据，保留记录）

第五版 G74（运行编号 `issue74-evidence.RO4o0YdT`，产品 `79a0568`、方案 `issue74-test-r5`）在调用者当前工作树位置执行：907 个方法开始并完成，41 个必需方法全部 `PASS`，但 16 个范围外 Stage 5 失败使整轮 `verdict` 为 `FAIL`。该运行暴露了第五版 Recipe 的 ambient-environment 缺陷，成为第六版重开依据，其脱敏 JSON 保留于 `evidence/issue-74/regression-r5-worktree-fail.json`，不删除。环境归属证据链（记录于该文件与本节）：同一内容在 `/tmp` 下多个独立检出（基线 `768b49e`、`74034af`、`79a0568`）均 `PASS`；在原位置对 `768b49e` 与 `74034af` 运行同一探针同样失败且失败集一致；CI（ubuntu、3.12）在 `79a0568` 全量通过——失败绑定原工作树位置携带的局部状态，先于本请求全部工作，与第 74 号产品无关。

另有一次执行尝试因误选第三版旧运行目录被判定入口防覆盖保护拒绝（退出码 2，零测试运行），按方案作废并记录，不构成重试采样。

## G74：第六版独立检出正式回归（运行编号 `issue74-evidence.5APqKFdD`）

- 按 r6 建立运行目录与独立检出：来源仓库 `git status --porcelain` 为空；`git clone --no-local --no-checkout` 至 `RUN_DIR/checkout` 后 `checkout --detach 3e118cf…`；检出 `HEAD` 与待测提交一致、状态干净；基线提交可读取。`SOURCE_REPO` 只提供 Git 对象，产品文件全部读取自独立检出。
- `TMPDIR` 指向运行目录内 `tmp`；`PYTHONDONTWRITEBYTECODE=1`；`UV_CACHE_DIR` 指向运行目录内 `uv-cache`。开始 `2026-10-03T11:10:04Z`，结束 `2026-10-03T11:13:30Z`（UTC，见运行目录 `start-time.txt` 与 `end-time.txt`）。
- 命令与 r6 G74 节逐字一致（五个 `--require-prefix`、`--pattern 'test_*.py'`）。

结构化字段与唯一判定逐项核对：`REGRESSION_EXIT` 0；`verdict` `PASS`；`tests_run` 907（大于 0）；`started` 与 `completed` 各 907、一致且编号唯一；`load_errors` 空、`interruption` null、`missing_required_prefixes` 空；`events`、`failures`、`errors`、`skipped`、`expected_failures`、`unexpected_successes` 全部为空；41 个必需方法全部存在；`complete-pass.json` 为 `true`；运行后独立检出 `git status --porcelain` 为空。**G74 唯一判定的全部条件满足，G74 为 `PASS`。**

机器证据：`evidence/issue-74/regression.json` 为本次运行的脱敏副本（删除 `cwd` 字段、临时目录绝对路径以占位符替代），保留全部 907 个方法及判定字段。41 个必需方法第三关口行动均为 `EXECUTE_CURRENT`；每方法的版本、命令、运行编号共用本节。

## P74：判定程序第二关口证明（复用）

`gate2_evidence.py`（`f7917830`）、`issue74_recipe_checks.py`、`issue-74-check-samples.jq`、`check-issue-74-pass-check.sh`、`test_issue74_recipe_observers.py` 相对第五版 Gate 2 通过来源（`df2e23a` 一线）`git diff` 为空；`3e118cf` 只修订 `test-plan/issue-74.md`。按 r6 记录 `REUSE_PRIOR_PASS`：来源为第三版官方检查（运行 `issue74-evidence.uiCE2ET6`，证据 `evidence/issue-74/` 下 observers/recipe-checks/evaluator-checks/completeness 四文件），影响分析：本轮 G74 依赖的判定通道、完整性脚本与观察器均未变化。

## S74：固定源码与文档检查（逐项满足）

静态产物五件（`product.diff` 基线至当前头、`shared-source.py`、`entry53.py`、`entry55.py`、`usage.md`，`DOC_PATH` = `.apm/skills/professor-contact/tests/README.md`）可由当前提交用方案命令再生。自上一记录（`3f4320f`）以来产品源码与使用说明零变化，本节结论沿用并复核：

1. **共用模块职责与调用链：满足。** 共用模块只含目录、文件、摘要与占用判定，无业务数据。第 53 号合法成功链 `check_mutually_independent` → `resolved_outside_producer`（双根）→ `check_roots_separated_from_claims` → `ensure_new_output` → `prepare_root`（双根；第二根失败走 `discard_created_root` 归属回滚）→ `write_json`（样例）→ `write_text`（资料）→ `file_sha256`（三摘要）→ `write_json_exclusive`（清单）；第 55 号同构（单根）。虚构数据由入口拥有；模块仅导入标准库，无浏览器、外部服务、代理或真实用户资料。占用路径生成（`claim_path_for` 内部编码）、冲突（锚点符号链接排他创建失败即拒，从不覆盖既有路径）、释放（`release`/`_discard_claim` 只删锚点与持有目录）与归属（`owned` 按 inode/设备、`discard_created_root` 仅新建且归属一致）完整；未取得占用者不清理他人状态。一个运行仍持有的占用（锚点符号链接存在）在调用方拼写与解析后拼写上、于准备与全部写入入口被拒绝作为另一运行的根、样例或清单位置。占用名称编码只用于定位真实锚点；无锚点的同形名称（含既有空目录与全新路径）保持合法。
2. **范围与判定程序：满足。** `product.diff` 全量核对：`.apm/skills/professor-contact/scripts/`、`SKILL.md`、`packages/`、`.apm/agents` 零变化；迁移范围仅两个既有入口与共用模块。判定入口相对基线零变化，产品失败优先、空执行非通过保持。差异中另含 `.github/workflows/ci.yml`（`fetch-depth: 0`，供观察器读取固定基线提交）与测试方案、根级 `test/test_issue74_recipe_observers.py`（第二关口提交引入），均非业务程序，已在第 76 号请求说明。
3. **使用说明：满足。** `usage.md`（74 行）区分共用准备、执行判定、问题专属样例与断言四类职责；含旧入口两种调用方式与参数、失败通道与退出约定、新增议题样例步骤、结构化判定两条红线、独立目录分配、异常占用拒绝接管与隔离空间整体清理责任；明确"是否属于实际占用只由锚点符号链接决定，与名称形状无关"，未把内部占用名称编码写成超出批准计划的永久用户路径限制。

## 与第三关口结论的关系

本轮执行后的事实：r6 独立检出 G74 唯一判定全部条件满足（`PASS`）；41 个必需方法全部对当前产品有效通过；S74 三项全部满足；无未解决的第 74 号产品失败。第五版运行的位置绑定 `FAIL` 作为重开依据保留，其环境归属已由上述证据链说明。第三关口与合并就绪的正式结论按方案归审核者对照本记录判定。
