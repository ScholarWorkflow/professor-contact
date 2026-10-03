# 第 74 号议题测试方案第 8 版

## 状态与唯一来源

- 修订号：`issue74-test-r8`。
- 本版修复第七版遗漏的一个验收 `false-FAIL`：无真实占用时，业务清单或第 53 号资料根使用首选内部锚点位置及其子路径，现有实现测试却要求拒绝。该预期与已批准计划“内部名称编码不得扩大合法输入拒绝范围、内部占用应避开业务路径”的约定冲突。
- 本版不修改正式需求、不修改已批准执行计划、不降低任何 PASS 条件，也不修改 `ABSOLUTE_PASS`。41 个必需方法名称与数量不变；只扩展既有 R2/R3 合法输入证明，修正四个实现测试的错误拒绝预期，并让两个辅助函数拒绝用例使用真实持有的占用而非未使用的候选名称。
- 本文件及当前 head 中的 `.apm/skills/professor-contact/tests/test_issue74_fixture_support.py`、`.apm/skills/professor-contact/tests/test_issue74_cross_run_claims.py`、`.apm/skills/professor-contact/tests/test_fixture_support.py`、`test-plan/issue-74-required-cases.json`、`test-plan/issue-74-pass-check.jq` 构成当前唯一权威测试方案正文。判定检查样例仍为 `test-plan/issue-74-check-samples.jq`、`test-plan/check-issue-74-pass-check.sh` 和 `.apm/skills/professor-contact/tests/issue74_recipe_checks.py`。
- 本版全部取代第七版 `issue74-test-r7`。第七版正式来源为提交 `90955c5a560d136a42de623b4bc603b60d720e56` 及 PR 76 评论 `https://github.com/ScholarWorkflow/professor-contact/pull/76#issuecomment-5969344015`（读取时更新时间 `2026-10-03T12:51:48Z`）；被审核输入为 `20b829d48e6fb55819ac4fa0c457a88b53cfe351`。历史方案和历史执行证据只作为来源记录，不需要执行者拼接。
- 正式需求：第 74 号议题需求第 1 版，R1—R4。
- 正式执行计划：`plan/issue-74.md` 第 3 版，提交 `a328e788a21af8fc7d3ebf052c399054d242b786`，已有正式批准。本次 Recipe 修订不重开计划审核。
- 兼容基准：`768b49ef4514e36edec6b57ed3821a99af9e9c00`。
- 判定语义保持 `ABSOLUTE_PASS`：正式 G74 中任何有效测试失败、错误、跳过、非零回归退出或总 `verdict != PASS` 都使 G74 为 `FAIL`。基线失败、范围外归属或“不是本 PR 引入”都不能把该次 G74 改写为 `PASS`。

## 第八版合法重开事实与修订结论

本次只重开 R2/R3“内部占用编码不能扩大合法输入拒绝范围”的 proof，满足 `Test Engineer Rule` §6.2 的三项事实：

1. **冻结要求／规则**：第三版批准计划要求允许收紧的旧输入仅限已冻结危险类别和真实并发占用冲突；其他合法输入不得借内部占用编码扩大拒绝范围。占用名称编码属于内部实现，普通内容占住首选内部名称时应改用其他内部名称；只有真实活动或异常遗留占用才属于必须拒绝的占用冲突。
2. **负责 Proof／Case**：第七版 R2/R3 的负责方法是 `test_issue74_cross_run_claims.Issue74CrossRunClaimTests.test_claim_like_paths_without_live_claim_remain_legal`；同时 G74 使用 `--pattern 'test_*.py'` 执行整个生产者测试目录，因此 `test_fixture_support.py` 中任何未经正式要求支持的失败预期也会直接改变 `ABSOLUTE_PASS` verdict。
3. **最小错误结果**：在生产者之外的空隔离目录中，程序根为 `program`、输出为 `.program.fixture-claim/manifest.json`，两者均不存在且没有真实占用，其余前提合法。满足要求的实现避开输出路径选择内部占用，产出兼容样例与清单并释放自有占用。被审版本 `test_fixture_support.py` 第 466、478、488、589 行起的四个用例却对输出或资料根的这种布局使用 `assertRaises`，合法成功会使 G74 失败。第七版合法证明只覆盖普通同名路径和普通符号链接，未覆盖业务路径恰好使用首选名称的错误拒绝，构成明确 `false-FAIL`。

分类：直接问题为 `RECIPE`；相同冻结要求下第七版 `PASS + COMPLETE` 漏审，另记 `REVIEW_DEFECT`。不重开正式要求或执行计划。

修复方式固定如下：既有正式方法 `test_claim_like_paths_without_live_claim_remain_legal` 保留第七版全部输入，并增加两个入口的清单等于或位于首选内部名称内的合法输入；第 53 号还覆盖资料根等于或位于首选内部名称内。四个错误拒绝用例改为核查成功、样例文件、清单内容与返回对象一致，且业务路径没有成为内部占用符号链接。两个辅助函数拒绝用例以 `prepare_root` 取得的真实占用为输入，不再把未使用的候选名称当作实际占用。既有真实占用拒绝、禁止副作用、回滚及异常遗留用例保留。方法总数仍为 41 个，不新增第二个证明负责者。

第八版执行前检查依据：两个入口和调用方式未变，隔离目录前提、证据格式、判定程序及通过条件未变；成功事实由输出 JSON 与返回对象、实际样例文件及路径类型直接断言，真实占用负例由已取得的持有对象建立，拒绝后核查持有状态及占用内容。正确合法成功不再被四项异常断言拒绝，未成功构建不能满足新增成功断言。本次只作测试源码和方案自洽核查，不执行正式 G74，也不将当前产品行为当作正确预期来源。

本次修订完成后的设计结论：`Test Engineer Gate 1: PASS`（复用未改变的冻结要求）；`Test Engineer Gate 2: PASS`；`Gate review completeness: COMPLETE`（按 §6.2 限定范围，并核对完整记录自洽）。此结论只确认测试设计；已知产品阻断项仍须由实现执行者修复，当前 `Gate 3: NOT_READY`。本版尚未在 PR 发布，不表示远端已取得本版正文；执行者必须取得含本文件及配套测试的完整固定提交后才能使用。

## 要求与证明归属

所有路径均相对于 `.apm/skills/professor-contact/`。

| 要求／证明 | 唯一负责者 | 直接证明 |
| --- | --- | --- |
| R2 成功结果兼容 | `test_issue74_fixture_support.Issue74FixtureTests.test_compatibility_bytes_manifest_hashes_and_returns` | 固定基准与当前版本的返回对象、文件字节、摘要和包装行为兼容 |
| R2 两种既有调用方式 | `test_cli_from_unrelated_directory_without_pythonpath` | 按文件加载和无关目录直接 CLI 均保持原约定 |
| R2/R3 内部占用名称不能扩大合法输入拒绝范围 | `test_issue74_cross_run_claims.Issue74CrossRunClaimTests.test_claim_like_paths_without_live_claim_remain_legal` | 无实际占用时四种同名路径、普通符号链接占用首选内部名称、清单使用首选名称及其子路径、第 53 号资料根使用首选名称及其子路径，均保持合法 |
| R3 预先危险路径与清单冲突 | `test_preexisting_conflicts_fail_before_any_sample_write` | 拒绝已冻结危险输入，拒绝前不写样例、不覆盖原内容 |
| R3 第 53 号双根独立 | `test_equal_and_nested_issue53_roots_are_rejected_without_changes` | 相等与互为祖先均拒绝 |
| R3 已有空目录身份保持 | `test_existing_empty_root_identity_is_preserved` | 不删除重建既有空目录 |
| R3 不同运行普通输出独立 | `test_different_runs_do_not_share_writable_outputs` | 一个运行的写入不改变另一个运行输出 |
| R3 同一真实路径占用与正常释放 | `test_overlapping_call_cannot_recreate_first_empty_root` | 第二调用不能接管第一调用持有的根 |
| R3 不同真实路径不能共享实际占用 | `test_issue74_cross_run_claims.Issue74CrossRunClaimTests.test_live_claim_directory_cannot_be_used_as_another_run_root` | 另一运行的实际占用目录不能成为本运行样例根 |
| R3 清单创建竞态 | `test_manifest_creation_race_preserves_competing_bytes_and_partial_samples` | 排他创建不覆盖竞争者并保留已写样例 |
| R3 第 53 号第二根失败回滚 | `test_second_root_failure_rolls_back_only_new_owned_first_root` | 只删除本次新建且仍归属本次的第一根 |
| R3 写入失败 | `test_sample_write_failure_preserves_partial_samples` | 保留部分样例并释放自有占用 |
| R3 异常占用 | `test_abrupt_exit_leaves_occupation_and_next_call_cannot_take_over` | 异常遗留占用拒绝接管 |
| R4 判定通道 | `test_gate2_evidence.Gate2EvidenceTests` 与 P74 | PASS、产品 FAIL、准备无效和空执行保持区分 |
| R1、R2 实际复用、R4 文档及非目标 | S74 | 固定源码与文档逐项检查 |
| 两入口既有业务验收 | G74 中 `test_issue53_stage4_runtime_assets` 与 `test_issue55_stage3_runtime_assets` | 继续使用现有断言，不降低条件 |

`test-plan/issue-74-required-cases.json` 继续固定 41 个必需方法：13 个第 74 号产品方法、24 个第 53／55 号既有方法、4 个判定方法。执行者不得临场增删。

## Gate 2 执行前检查

本版不增加真实安装、代理、MCP、浏览器、外部进程或第三方服务依赖。正式产品证明仍是 producer-local deterministic test。

第七版已经冻结的独立检出环境继续原样有效：从当前干净仓库通过本地 Git 对象建立一个位于系统临时目录下的独立检出，并在该检出中运行冻结命令。本版只改变受影响合法输入及真实占用负例的测试断言，不改变该环境前提、结构化证据格式或判定程序。

正式执行前必须确认：

- 来源仓库 `git status --porcelain` 为空；否则停止，G74 为 `CASE_NOT_STARTED`。
- 待测提交可由 `git rev-parse HEAD` 精确取得。
- 固定兼容基准 `768b49ef4514e36edec6b57ed3821a99af9e9c00` 在本地对象库可读取；否则停止，G74 为 `CASE_NOT_STARTED`。
- 独立检出必须位于来源仓库及其 worktree 之外；不得复制当前工作树文件、不得使用符号链接、不得在独立检出中手工修补文件。
- 独立检出的 `HEAD` 必须与记录的待测提交完全相同，且 `git status --porcelain` 为空。

这些检查只确认执行位置与版本，不运行验收业务。

## 正式运行环境

正式 G74 只能按以下步骤建立运行目录和独立检出。`SOURCE_REPO` 只提供 Git 提交对象；正式测试不得从 `SOURCE_REPO` 工作树读取产品文件。

```sh
SOURCE_REPO=$(git rev-parse --show-toplevel)
SOURCE_SHA=$(git -C "$SOURCE_REPO" rev-parse HEAD)
test -z "$(git -C "$SOURCE_REPO" status --porcelain)" || exit 2
git -C "$SOURCE_REPO" cat-file -e 768b49ef4514e36edec6b57ed3821a99af9e9c00^{commit} || exit 2

RUN_DIR=$(mktemp -d "${TMPDIR:-/tmp}/issue74-evidence.XXXXXXXX")
CHECKOUT="$RUN_DIR/checkout"
mkdir -p "$RUN_DIR/tmp" "$RUN_DIR/uv-cache"

git clone --no-local --no-checkout "$SOURCE_REPO" "$CHECKOUT"
git -C "$CHECKOUT" checkout --detach "$SOURCE_SHA"
test "$(git -C "$CHECKOUT" rev-parse HEAD)" = "$SOURCE_SHA" || exit 2
test -z "$(git -C "$CHECKOUT" status --porcelain)" || exit 2
git -C "$CHECKOUT" cat-file -e 768b49ef4514e36edec6b57ed3821a99af9e9c00^{commit} || exit 2

printf '%s\n' "$SOURCE_REPO" > "$RUN_DIR/source-repo.txt"
printf '%s\n' "$SOURCE_SHA" > "$RUN_DIR/product-sha.txt"
printf '%s\n' "$CHECKOUT" > "$RUN_DIR/checkout-path.txt"

export TMPDIR="$RUN_DIR/tmp"
export PYTHONDONTWRITEBYTECODE=1
export UV_CACHE_DIR="$RUN_DIR/uv-cache"
cd "$CHECKOUT"

git log -1 --format=%H -- \
  test-plan/issue-74.md \
  .apm/skills/professor-contact/tests/test_issue74_fixture_support.py \
  .apm/skills/professor-contact/tests/test_issue74_cross_run_claims.py \
  .apm/skills/professor-contact/tests/test_fixture_support.py \
  test-plan/issue-74-required-cases.json \
  test-plan/issue-74-pass-check.jq > "$RUN_DIR/recipe-sha.txt"
git log -1 --format=%H -- \
  .apm/skills/professor-contact/tests/gate2_evidence.py > "$RUN_DIR/evaluator-sha.txt"
uv --version > "$RUN_DIR/uv-version.txt"
uv run --no-project --python 3.12 python -V > "$RUN_DIR/python-version.txt"
```

禁止用已有 worktree、旧运行目录、旧 checkout 或当前调用者工作树代替 `CHECKOUT`。禁止在 clone 后复制、覆盖或修补产品／测试文件。若创建独立检出失败，保存原始错误并停止，不改用原工作树继续执行。

## G74：一次正式完整回归

工作目录固定为上节的独立 `CHECKOUT`。命令、输入和判定条件如下，失败后不得缩小范围或改成定向运行来取得通过结果。

```sh
uv run --no-project --python 3.12 \
  .apm/skills/professor-contact/tests/gate2_evidence.py \
  --start .apm/skills/professor-contact/tests \
  --pattern 'test_*.py' \
  --require-prefix test_issue74_fixture_support.Issue74FixtureTests. \
  --require-prefix test_issue74_cross_run_claims.Issue74CrossRunClaimTests. \
  --require-prefix test_issue53_stage4_runtime_assets.Issue53Stage4RuntimeAssetTests. \
  --require-prefix test_issue55_stage3_runtime_assets.Issue55Stage3RuntimeAssetTests. \
  --require-prefix test_gate2_evidence.Gate2EvidenceTests. \
  --out "$RUN_DIR/regression.json" \
  > "$RUN_DIR/regression.stdout" \
  2> "$RUN_DIR/regression.stderr"
REGRESSION_EXIT=$?
printf '%s\n' "$REGRESSION_EXIT" > "$RUN_DIR/regression-exit.txt"

jq '{schema_version,python,cwd,selection,tests_run,started,completed,events,failures,errors,skipped,expected_failures,unexpected_successes,missing_required_prefixes,load_errors,interruption,verdict}' \
  "$RUN_DIR/regression.json"
jq --slurpfile required test-plan/issue-74-required-cases.json \
  -f test-plan/issue-74-pass-check.jq \
  "$RUN_DIR/regression.json" > "$RUN_DIR/complete-pass.json"
jq -e '. == true' "$RUN_DIR/complete-pass.json"
printf '%s\n' "$(git status --porcelain)" > "$RUN_DIR/checkout-status-after.txt"
```

### G74 唯一判定

`PASS` 必须同时满足：

- `REGRESSION_EXIT == 0`；
- `regression.json.verdict == "PASS"`；
- `tests_run > 0`；
- `started` 与 `completed` 完全一致、编号唯一；
- `load_errors == []`、`interruption == null`、`missing_required_prefixes == []`；
- `events`、`failures`、`errors`、`skipped`、`expected_failures`、`unexpected_successes` 全为空；
- 41 个必需方法全部存在；
- `complete-pass.json` 为 `true`；
- 独立 `CHECKOUT` 运行后 `git status --porcelain` 仍为空。

任何一项不满足都不能写 G74 `PASS`。有效测试失败或错误按 `ABSOLUTE_PASS` 判 G74 `FAIL`，无论它是否属于第 74 号业务范围、是否在基线也失败、是否被认为是既有失败。若环境或证据在测试启动前无效则为 `CASE_NOT_STARTED`；启动后证据失效按规则记 `INVALID_TEST_EXECUTION`。不得把 `FAIL` 改写成 `BLOCKED` 或“范围外所以通过”。

## P74：判定程序第二关口证明

P74 继续使用第七版来源提交 `90955c5a560d136a42de623b4bc603b60d720e56` 中已经通过的判定通道验证和完整性样例。以下文件从该提交到被审核产品提交 `20b829d48e6fb55819ac4fa0c457a88b53cfe351` 的内容比较无差异，本版也未修改它们，因此本轮 P74 采用 `REUSE_PRIOR_PASS`；复用的是判定程序设计证明，不是新增产品输入的执行结果：

- `.apm/skills/professor-contact/tests/gate2_evidence.py`
- `.apm/skills/professor-contact/tests/issue74_recipe_checks.py`
- `test-plan/issue-74-check-samples.jq`
- `test-plan/issue-74-pass-check.jq`
- `test-plan/check-issue-74-pass-check.sh`
- `test/test_issue74_recipe_observers.py`

任一文件变化命中判定或观察假设时，先重开对应 P74 proof；不得静默复用。

## S74：当前产品源码与文档静态检查

S74 读取当前待测提交的固定源码与文档，不从调用者原工作树读取。至少完整检查：

1. `tests/runtime/fixture_support.py` 只负责目录、文件、摘要和占用操作；第 53、55 号入口的合法成功调用链确实复用共用目录准备、写入和摘要能力；虚构业务数据仍由调用方拥有；没有浏览器、外部服务、代理或真实用户资料路径。
2. 占用生成、冲突、释放和归属符合已批准计划：相同真实路径竞争同一占用；若两个调用同时竞争同一候选锚点，后到调用在原子发布失败后必须先识别该候选是否已经成为真实占用，不能把同一路径转而发布成第二个回退锚点；普通内容占用内部候选名时才可继续寻找其他内部名；实际最终选择的首选或回退锚点均不得与本次根目录、样例文件或清单输出相等或形成包含关系；其他运行仍持有或异常遗留的实际占用不能被接管；未取得占用者不能清理他人状态；占用不能进入另一运行的样例或清单；内部占用名称编码不能在没有实际占用或其他冻结危险条件时永久禁用普通路径。
3. 迁移范围外业务程序、状态接口、代理配置及其他议题验收断言没有被本议题修改；判定程序若变化必须先分析影响。
4. `tests/README.md` 区分共用准备、执行与判定、问题专属样例和断言四项职责；记录旧入口调用、独立目录分配、异常占用拒绝接管、隔离空间清理责任和结构化结果判断；不得把内部占用编码写成永久用户路径限制。

每项记录准确文件、位置、满足／不满足和依据。文件存在或作者说明不能代替内容检查。

产品源码或 README 自上次有效 S74 后发生变化时采用 `REJUDGE_PRIOR_EVIDENCE` 仅限旧静态产物完整覆盖当前字节的情况；字节变化影响上述事实时重新生成静态产物并重新判断。单纯本 Recipe 文本变化不自动使未受影响的产品源码 S74 失效。

## 执行尝试、重试与证据

- 正式 G74 不允许因结果不理想自动重试。
- clone、解释器准备、磁盘或其他基础设施问题发生在测试启动前时，保留原始错误并停止；修复环境后必须使用新的 `RUN_DIR` 和新的运行编号，并把前次尝试完整保留为 `CASE_NOT_STARTED` 来源。
- 测试一旦有效启动，不得因出现 `FAIL` 再换工作目录、删失败测试、改参数、换判定脚本或重复采样。
- 正式记录至少保存产品提交、Recipe 提交、判定程序提交、运行编号、`CHECKOUT`、解释器版本、uv 版本、完整命令、结构化 JSON、完整通过结果和运行前后工作树状态。
- 提交仓库的证据只保留证明所需的最小脱敏内容；不得提交临时探针、运行目录或与判定无关的环境文件。

## 历史执行结果的处理

第五版运行 `issue74-evidence.RO4o0YdT` 保持其原始事实：907 个方法有效运行，41 个必需方法通过，但整轮 `verdict == FAIL`、回归退出码 1、`complete-pass == false`。它仍是第六版环境修订的重开依据，不得重新判为 `PASS`。

第六版运行 `issue74-evidence.Vf9dEgan` 保持其原始事实：909 个方法有效运行，41 个必需方法和整轮 `ABSOLUTE_PASS` 均通过。该运行证明的是第六版 Recipe 与当时测试输入，不能作为第八版新增合法输入已经执行的证明。

第七版执行者评论 `https://github.com/ScholarWorkflow/professor-contact/pull/76#issuecomment-5969994577`（读取时更新时间 `2026-10-03T14:15:17Z`）报告运行 `issue74-evidence.AH8XmYKm` 的 912 项通过，产品记录提交为 `20b829d48e6fb55819ac4fa0c457a88b53cfe351`。本版不追溯改写该次执行事实，也未在本轮重新审核其全部原始机器证据；新增合法输入和修正后的断言没有在该次运行中执行，不能复用或重新判读为第八版 G74 的通过结果。

第八版 G74 选择 `EXECUTE_CURRENT`：四个错误拒绝预期、真实占用负例前提及正式合法输入均已变化，旧证据不含本版待判事实，不能仅靠重新判读取得通过。产品修复且本版配套测试已进入待测提交后，必须按上述独立检出 Recipe 执行一次完整回归；不得执行第七版测试来证明第八版通过。未受影响的需求、执行计划和测试证明设计复用第七版来源；G74 使用已冻结整套回归且保持 `ABSOLUTE_PASS`，故其当前正式执行仍包含全部测试，不增加额外业务执行。

P74 采用上述准确来源的 `REUSE_PRIOR_PASS`。S74 当前已有未解决的产品阻断项：同一真实根可能因不同业务路径取得不同占用，及解析后的实际占用目录可被另一调用写入；这些事实已经属于第七版 S74 第 2 项，不因发现它们重开未受影响的测试设计。实现执行者修复后，S74 对占用选择、实际目录识别、写入及释放的直接连带路径采用 `EXECUTE_CURRENT` 静态核查，记录当前源码位置与依据；没有新有效结论前不能复用旧结论写就绪。

## Gate 3 记录要求

Gate 3 对每个必需 proof 记录：

- Requirement／Proof／Case ID；
- `EXECUTE_CURRENT`、`REUSE_PRIOR_PASS` 或 `REJUDGE_PRIOR_EVIDENCE`；
- 准确产品、Recipe、判定和证据版本；
- 原始证据位置、运行编号和命令；
- 影响分析及最终 verdict。

第八版 G74 固定为 `EXECUTE_CURRENT`。只有三个 Gate 均为 `PASS`、S74 满足、G74 满足上述 `ABSOLUTE_PASS`、41 个必需方法对当前产品版本均有有效 PASS，且没有未解决的 producer `FAIL` 或必需 case 的非通过终态，才能记录：

`Merge conclusion: READY`

在新的正式 G74 完成前：

`Gate 3: NOT_READY`

`Merge conclusion: NOT_READY`
