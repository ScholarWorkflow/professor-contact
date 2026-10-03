# 第 74 号议题第五版测试执行与静态检查结果（执行者记录）

本记录由本地执行 agent 按第五版冻结方案（`issue74-test-r5`）执行一次 G74 并完成 S74 后发布。发布只新增执行证据与静态产物引用，不修订测试方案、验收条件、需求或执行计划。按方案第 2 节，执行者保存证据，审核者判断有效性；第三关口结论与合并就绪判断归审核者，本记录不代替该判断。

## 输入与版本

- 正式需求：[第 74 号议题需求第 1 版](https://github.com/ScholarWorkflow/professor-contact/issues/74)，R1—R4，读取更新时间 `2026-10-02T16:02:24Z`。
- 执行计划：[第三版](https://github.com/ScholarWorkflow/professor-contact/blob/a328e788a21af8fc7d3ebf052c399054d242b786/plan/issue-74.md)，批准保留，本轮变化不触发重开。
- 测试方案：`issue74-test-r5`，方案提交 `947a4ee111707abdf5ce213586df6d5461bbd050`（`git log -1 -- test-plan/issue-74.md` 及配套四个方案文件）。
- 产品提交：`79a0568d6b92d07d83ab20b8d7d3a66482a27619`；兼容基准 `768b49ef4514e36edec6b57ed3821a99af9e9c00`。
- 判定入口：`.apm/skills/professor-contact/tests/gate2_evidence.py`，最后修改提交 `f7917830d34f7b107f757cf2b6a476cc752631ab`（与第三版官方运行一致）。
- 环境：CPython 3.12.13（`uv run --no-project --python 3.12`）、uv 0.12.11、macOS。运行前后 `git status --porcelain` 为空。

## 一次中止的执行尝试（操作错误记录）

第一次执行前，操作者以 `ls | tail -1` 复用运行目录时误选了第三版官方运行的旧目录；冻结判定入口的防覆盖保护以 `--out already exists` 拒绝执行（退出码 2），零个测试被运行，随后对该旧目录内旧证据的读取不构成任何本轮执行。按方案"基础设施故障保存完整尝试并停止"处理：该尝试作废，换新运行目录重新完整执行；不构成重试采样，本轮正式结果只来自下述唯一一次运行。

## G74：一次正式回归（运行编号 `issue74-evidence.RO4o0YdT`）

- 开始 `2026-10-03T10:14:07Z`，结束 `2026-10-03T10:17:25Z`（UTC，见运行目录 `start-time.txt` 与 `end-time.txt`）。
- 独立运行目录由 `mktemp` 分配并导出为 `TMPDIR`；`PYTHONDONTWRITEBYTECODE=1`；`UV_CACHE_DIR` 指向运行目录内 `uv-cache`；仓库检出运行前后干净。
- 命令与第五版第 G74 节逐字一致（五个 `--require-prefix`、`--pattern 'test_*.py'`、输出到 `$RUN_DIR/regression.json`）。

结构化字段：`tests_run` 907；`started` 与 `completed` 各 907 且一致、编号唯一；`load_errors` 0；`interruption` null；`missing_required_prefixes` 空；`failures` 15、`errors` 1、`skipped` 0（见下节归属）；`verdict` `FAIL`；回归退出码 1。按 `ABSOLUTE_PASS`，该整轮 `FAIL` 如实保留，不被任何基线失败抵消。

41 个必需方法（13 个第 74 号产品方法、24 个既有第 53／55 号方法、4 个判定方法）：全部出现在 `started` 且无一拥有非通过事件，逐一为 `PASS`，其中第四版 live claim 用例与第五版合法名称用例均为 `EXECUTE_CURRENT`。`issue-74-pass-check.jq` 的完整通过检查为 `false`，唯一原因是上式要求整轮 `verdict == "PASS"`，而整轮判定被下节范围外失败阻断；41 个必需方法本身的缺席检查与非通过事件检查均为 0。

### 范围外失败的归属与环境证据

16 个非通过事件全部位于 `test_contact_state.TestStage5`（12）与 `test_stage5_immutable`（4），属 Stage 5 邮件链路自身要求，不在第 74 号范围，也不在 41 个必需方法内。其归因为**本机特定位置下的既有环境现象**，证据链：

1. 位置绑定：同一提交的相同内容在 `/tmp` 下多个检出（含基线 `768b49e`、`74034af`、当前 `79a0568`）运行该模块均 `PASS`（22 测试 0 失败）；仅在本仓库工作树原位置失败。
2. 早于本请求：在原位置对基线提交 `768b49e` 与产品 `74034af` 运行同一探针同样失败（11 失败 1 错误），失败集与本轮一致——先于本 PR 全部工作存在。
3. CI（ubuntu、Python 3.12）在 `79a0568` 上全量通过。

按方案"完整回归的既有范围外失败按其原要求归属判断"，该 16 个失败归属 Stage 5 既有验收，不扩大第 74 号产品要求；同时按 `ABSOLUTE_PASS` 不掩盖整轮未就绪，整轮 `FAIL` 如实进入本记录。

机器证据：`evidence/issue-74/regression.json` 为本次运行的脱敏副本（删除 `cwd` 字段，个人主目录、工作树与临时目录绝对路径以占位符替代），保留全部 907 个方法及判定字段；每个方法的版本、命令、运行编号共用本节；41 个必需方法第三关口行动均为 `EXECUTE_CURRENT`。

## P74：第二关口检查复用

判定入口 `f7917830`、观察器 `test/test_issue74_recipe_observers.py`、完整性脚本 `check-issue-74-pass-check.sh`、判定样例 `issue-74-check-samples.jq`、`issue-74-pass-check.jq` 自第三版官方检查（运行 `issue74-evidence.uiCE2ET6`，证据见 `evidence/issue-74/` 其余四个文件）以来 `git diff` 为空，符合方案"未变化检查按准确历史来源复用"。第三版 P74 记录继续有效：三通道判定、失败后清理仍保留失败、空执行与缺少证明不能通过均已确认。

## S74：固定源码与文档检查（逐项满足）

静态产物（对 `79a0568` 生成，随本提交可追溯）：`product.diff`（基线至 `79a0568`）、`shared-source.py`、`entry53.py`、`entry55.py`、`usage.md`（`DOC_PATH` = `.apm/skills/professor-contact/tests/README.md`）。

1. **共用模块职责与调用链：满足。** 共用模块只含目录、文件与摘要操作及占用判定，无业务数据。第 53 号合法成功链：`check_mutually_independent` → `resolved_outside_producer`（双根）→ `check_roots_separated_from_claims` → `ensure_new_output` → `prepare_root`（双根，第二根失败走 `discard_created_root` 归属回滚）→ `write_json`（样例）→ `write_text`（资料）→ `file_sha256`（三摘要）→ `write_json_exclusive`（清单）；第 55 号同构（单根）。虚构数据 `_candidate_state`/`_stage2_input` 由入口拥有；模块仅导入标准库，无浏览器、外部服务、代理或真实用户资料路径。占用路径生成（`claim_path_for` 内部编码）、冲突（锚点排他创建失败即拒）、释放（`release`/`_discard_claim` 只删锚点与持有目录）与归属（`owned` 按 inode/设备、`discard_created_root` 仅新建且归属一致）完整；未取得占用者不清理他人状态。一个运行仍持有的占用（锚点符号链接存在）在调用方拼写与解析后拼写上、于准备与全部写入入口被拒绝作为另一运行的根、样例或清单位置。占用名称编码只用于定位真实锚点；无锚点的同形名称（含既有空目录与全新路径）保持合法，无永久禁用命名空间。
2. **范围与判定程序：满足。** 迁移范围仅两个既有入口与共用模块；业务脚本、状态接口、代理配置、其他议题断言未改（`product.diff` 全量核对：`.apm/skills/professor-contact/scripts/`、`SKILL.md`、`packages/`、`.apm/agents` 零变化）。判定入口相对基线零变化，产品失败优先、空执行非通过语义保持。差异中另含 `.github/workflows/ci.yml`（`fetch-depth: 0`，供观察器读取固定基线提交）与测试方案文件、根级 `test/test_issue74_recipe_observers.py`（第二关口提交引入），均非业务程序，已在第 76 号请求说明。
3. **使用说明：满足。** `usage.md`（74 行）区分共用准备、执行判定、问题专属样例与断言四类职责；含旧入口两种调用方式与参数、失败通道与退出约定、新增议题样例步骤、结构化判定两条红线、独立目录分配、异常占用拒绝接管与隔离空间整体清理责任；明确"是否属于实际占用只由锚点符号链接决定，与名称形状无关"，未把内部占用名称编码写成超出批准计划的永久用户路径限制。

## 与第三关口结论的关系

本轮执行后的事实：41 个必需方法全部对产品 `79a0568` 有效通过；S74 三项全部满足；整轮 `verdict` 为 `FAIL`，唯一来源是 16 个位置绑定的范围外 Stage 5 既有失败（证据见上）。按方案最终条件，合并就绪须由审核者对照本记录与第五版方案判定；本记录不自行宣布 `Gate 3: PASS` 或合并就绪。
