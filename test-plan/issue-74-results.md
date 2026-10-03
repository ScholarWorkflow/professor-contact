# 第 74 号议题第八版测试执行与静态检查结果（执行者记录）

本记录由本地执行 agent 按第八版冻结方案（`issue74-test-r8`）执行 G74 并完成 S74 后发布。按方案第 2 节，执行者保存证据，审核者判断有效性；第三关口结论与合并就绪判断归审核者，本记录不代替该判断。

## 输入与版本（当前有效）

- 正式需求：[第 74 号议题需求第 1 版](https://github.com/ScholarWorkflow/professor-contact/issues/74)，R1—R4，读取更新时间 `2026-10-02T16:02:24Z`。
- 执行计划：[第三版](https://github.com/ScholarWorkflow/professor-contact/blob/a328e788a21af8fc7d3ebf052c399054d242b786/plan/issue-74.md)，批准保留；r5—r8 四次 Recipe 修订均不触发计划重开。
- 测试方案：`issue74-test-r8`，提交 `8db7ae7111bc6b8be70a41a7fe331d216180adc7`（r8 修复第七版遗漏的验收 `false-FAIL`：无真实占用时业务清单或第 53 号资料根使用首选内部锚点位置及其子路径必须合法，四个错误拒绝用例改为成功断言，两个辅助函数拒绝用例改用真实持有的占用）。
- 产品提交：`2768878f66363c651fa18920d8926cfe10248b2e`（执行者按 r8 方案第 8 节记录的两条产品阻断项完成修复，详见 S74 第 2 项）。兼容基准 `768b49ef4514e36edec6b57ed3821a99af9e9c00`。
- 判定入口：`.apm/skills/professor-contact/tests/gate2_evidence.py`，提交 `f7917830d34f7b107f757cf2b6a476cc752631ab`（与第三版官方运行一致）。
- 环境：CPython 3.12.13（`uv run --no-project --python 3.12`）、uv 0.12.11、macOS。

## G74：第八版独立检出正式回归（运行编号 `issue74-evidence.PCkFcSQ4`，当前有效）

- 独立检出：来源仓库 `git status --porcelain` 为空；`git clone --no-local --no-checkout` 至 `RUN_DIR/checkout` 后 `--detach 2768878…`；`HEAD` 与待测提交一致、状态干净；基线提交可读取。`SOURCE_REPO` 只提供 Git 对象。
- `TMPDIR` 指向运行目录内 `tmp`；`PYTHONDONTWRITEBYTECODE=1`；`UV_CACHE_DIR` 指向运行目录内 `uv-cache`。回归命令 `2026-10-03T15:38:09Z` 启动、`2026-10-03T15:41:38Z` 完成；单次执行、无重试。
- 命令与 r7 G74 节逐字一致（五个 `--require-prefix`、`--pattern 'test_*.py'`）。

结构化字段与唯一判定逐项核对：`REGRESSION_EXIT` 0；`verdict` `PASS`；`tests_run` 912（大于 0）；`started` 与 `completed` 各 912、一致且编号唯一；`load_errors`、`events`、`failures`、`errors`、`skipped`、`expected_failures`、`unexpected_successes`、`missing_required_prefixes` 全部为空；`interruption` null；41 个必需方法全部存在；`complete-pass.json` 为 `true`；运行后独立检出 `git status --porcelain` 为空。**G74 唯一判定全部条件满足，G74 为 `PASS`。** 41 个必需方法行动均为 `EXECUTE_CURRENT`（r8 新增与修正断言全部在该次运行中实际执行）。

机器证据：`evidence/issue-74/regression.json` 为本次运行的脱敏副本（删除 `cwd` 字段，个人主目录与临时目录绝对路径不进入仓库），保留全部 912 个方法及判定字段。每方法的版本、命令、运行编号共用本节。

## P74：判定程序第二关口证明（复用）

`gate2_evidence.py`（`f7917830`）、`issue74_recipe_checks.py`、`issue-74-check-samples.jq`、`check-issue-74-pass-check.sh`、`test_issue74_recipe_observers.py` 六个文件从 r8 记载的 Gate 2 来源 `90955c5a…` 经被审产品 `20b829d4…` 到当前产品 `2768878f…` 的 `git diff` 均为空（本次修复仅改 `tests/runtime/fixture_support.py`，未触碰判定通道）。记录 `REUSE_PRIOR_PASS`：来源为第三版官方检查（运行 `issue74-evidence.uiCE2ET6`，证据 `evidence/issue-74/` 下 observers/recipe-checks/evaluator-checks/completeness 四文件），影响分析：G74 依赖的判定通道、完整性脚本与观察器均未变化。

## S74：固定源码与文档检查（修复后对 `2768878` 逐项 `EXECUTE_CURRENT` 静态核查）

r8 方案第 8 节记载的两条产品阻断项已由 `2768878` 修复；本节按方案要求对占用选择、实际目录识别、写入及释放的直接连带路径记录当前源码位置与依据。行号以 `2768878` 的 `tests/runtime/fixture_support.py` 为准。

1. **共用模块职责与调用链：满足。** 共用模块只含目录、文件、摘要与占用判定，无业务数据；仅导入标准库，无浏览器、外部服务、代理或真实用户资料。第 53 号合法成功链 `check_mutually_independent` → `resolved_outside_producer`（双根）→ `check_roots_separated_from_claims` → `ensure_new_output` → `prepare_root`（双根；第二根失败走 `discard_created_root` 归属回滚）→ `write_json`（样例）→ `write_text`（资料）→ `file_sha256`（三摘要）→ `write_json_exclusive`（清单）；第 55 号同构（单根）。虚构数据由入口拥有（入口文件 `prepare_issue53_stage4_fixture.py`、`prepare_issue55_stage3_fixture.py`）。
2. **占用生成、冲突、释放和归属：满足（两条阻断项的修复依据如下）。**
   - **阻断项一（同一真实根因不同业务路径取得不同占用）→ 修复。** `_publish_anchor`（`fixture_support.py` 第 339—391 行）改为两段式：第一段对整个确定性锚点名序列（首选名及 `.{首选名}.r2`、`.r3`…共 64 个候选）做整体真实占用探测，任一候选携带真实占用即整体冲突拒绝（第 369—372 行）；第二段才在无真实占用的候选中按序选择，普通内容候选与本次业务路径候选只影响选择、不影响冲突判定（第 372—388 行）。因此两个调用准备同一真实根时，无论各自业务路径占用哪个内部名称，后到调用都会在整体探测中发现先到调用持有的锚点并拒绝，不再可能各自持有不同锚点并行写入同一真实根。`overlaps_business` 的业务路径先经 `Path.resolve()` 归一化再作字典序比较（第 354—358 行），避免 `/var` 与 `/private/var` 这类符号链接前缀拼写差异漏判重合。
   - **阻断项二（解析后的实际占用目录可被另一调用写入）→ 修复。** 占用目录在创建并写入内部持有标记后立即由 `_seal_held_dir`（第 297—309 行）`chmod(0o500)` 只读封闭（第 426 行调用点）；此后任何调用（包括直接使用解析后绝对路径的调用）在其中的创建与写入由内核在操作时拒绝，无检查-写入竞态。四个直接连带写入路径把该拒绝转为显式 `FixtureBuildError`：`_mkdir_parents_claim_free`（第 128—131 行）、`prepare_root` 的根创建（第 455—459 行）、`write_text`（第 489—493 行）、`write_json_exclusive`（第 515—519 行）。释放是唯一恢复写入的路径：`_remove_held_dir`（第 312—328 行）先 `chmod(0o700)` 再删标记与目录，且仅在 `_discard_claim`（第 331—336 行）已原子 unlink 本运行锚点之后调用；未取得占用者无法触碰他人占用目录内容，异常遗留（锚点在、目录只读）继续按既有规则拒绝接管并报告。
   - **发布竞态与回退约束（r7 既有要求，复核仍满足）。** 原子 `os.symlink` 发布失败（`EEXIST`）后重分类：该候选已成真实占用则整体冲突，绝不把同一路径转而发布成第二个回退锚点；仅普通内容才移到下一内部名（第 383—387 行）。实际选中的首选或回退锚点与本次根、样例、清单输出互不相等、互不包含（`overlaps_business`，第 354—358 行）；`check_roots_separated_from_claims`（第 187—214 行）与 `ensure_new_output` 的 claims 检查（第 243—254 行）只对携带内部持有标记的真实占用（`_is_live_claim`，第 56—72 行）拒绝，未使用候选名保持普通合法路径；占用识别在调用方拼写与解析后拼写上、于准备与全部写入入口执行（`resolved_outside_producer`、`ensure_new_output`、`write_text`、`write_json_exclusive` 的 raw+resolved 双重检查）。归属仍按 inode/设备（`owned`，第 270—277 行），`discard_created_root` 仅删除本运行新建且归属一致的根（第 468—477 行）。
   - **动态验证（执行者自查，不作为正式用例）。** 在调用者工作树以 `prepare_root(business_paths=[首选锚点内清单])` 模拟先到运行（锚点落在 `.r2`），随后同根正常清单的第二入口被整体探测拒绝且先到持有完好；对解析后占用目录的直接写入、写入原语与 `mkdir` 均被拒绝，目录模式 `0o500`；释放后锚点与占用目录均消失。
3. **范围与判定程序：满足。** 本次修复提交仅改 `tests/runtime/fixture_support.py`（113 增 42 删）；`.apm/skills/professor-contact/scripts/`、`SKILL.md`、`packages/`、`.apm/agents` 零变化；迁移范围仅两个既有入口与共用模块。判定入口相对基线零变化，产品失败优先、空执行非通过保持。差异中另含 `.github/workflows/ci.yml`（`fetch-depth: 0`）与测试方案、根级 `test/test_issue74_recipe_observers.py`，均非业务程序；无运行产物或临时探针。
4. **使用说明：满足。** `tests/README.md`（方案 `DOC_PATH`）区分共用准备、执行判定、问题专属样例与断言四类职责；识别语义为"是否属于实际占用只由锚点符号链接及内部持有标记决定，与名称形状无关"；含旧入口两种调用方式与参数、失败通道与退出约定、新增议题样例步骤、结构化判定两条红线、独立目录分配、异常占用拒绝接管与隔离空间整体清理责任；未把内部占用名称编码写成永久用户路径限制。r8 未改该文件，其内容与 `2768878` 行为一致。

## 历史运行记录（重开依据与过程，保留）

### 第五版 G74（运行编号 `issue74-evidence.RO4o0YdT`，位置绑定 `FAIL`，重开依据）

在调用者当前工作树位置执行：907 个方法开始并完成，41 个必需方法全部 `PASS`，但 16 个范围外 Stage 5 失败使整轮 `verdict` 为 `FAIL`。该运行暴露了第五版 Recipe 的 ambient-environment 缺陷，成为第六版重开依据；脱敏 JSON 保留于 `evidence/issue-74/regression-r5-worktree-fail.json`，不删除。环境归属证据链：同一内容在 `/tmp` 下多个独立检出（基线 `768b49e`、`74034af`、`79a0568`）均 `PASS`；在原位置对 `768b49e` 与 `74034af` 运行同一探针同样失败且失败集一致；CI（ubuntu、3.12）在 `79a0568` 全量通过——失败绑定原工作树位置携带的局部状态，先于本请求全部工作，与第 74 号产品无关。

### 第六版至第七版首跑（历史）

- `issue74-evidence.5APqKFdD`（产品 `3e118cf`，r6）：907 个方法全部通过，41 个必需方法全部 `PASS`。之后审核者发现两项 `PRODUCT` 问题（锚点编码冲突、清单写入竞态）及一个执行偏离（临时探针），由 `45fdfa9` 修复并删除。
- `issue74-evidence.Vf9dEgan`（产品 `45fdfa9`，r6 重执行）：909 个方法全部通过，41 个必需方法全部 `PASS`；r7 以普通符号链接合法面取代。
- `issue74-evidence.vyhmHAsr`（产品 `da9f5b4`，r7 首跑）：909 个方法全部通过，41 个必需方法全部 `PASS`。之后审核者发现两项 `PRODUCT` 问题（发布冲突未重分类、回退候选未核对业务路径），由 `9e6b82a` 修复。
- `issue74-evidence.AH8XmYKm`（产品 `9e6b82a`，r7）：912 个方法全部通过，41 个必需方法全部 `PASS`；r8 以业务路径使用首选锚点位置的合法面与真实占用负例修正取代，该次运行不再作为当前 PASS 来源。

### 中止的执行尝试

第五版首次执行前，操作者误选第三版旧运行目录，被判定入口防覆盖保护拒绝（退出码 2，零测试运行），按方案作废并记录；正式结果只来自各节记录的运行。

## 与第三关口结论的关系

当前事实：r8 独立检出 G74 唯一判定全部条件满足（`PASS`，对产品 `2768878`，方案 `8db7ae7`）；41 个必需方法全部有效通过；方案第 8 节记载的两条产品阻断项已修复并逐项静态核查；P74 按准确来源复用；S74 四项对 `2768878` 逐项满足；无未解决的第 74 号产品失败。第三关口与合并就绪的正式结论按方案归审核者对照本记录判定。
