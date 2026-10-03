# 第 74 号议题测试方案第 7 版

## 状态与唯一来源

- 修订号：`issue74-test-r7`。
- 本版只修复第六版的一个验收 `false-FAIL`：第六版后的实现测试把“首选内部锚点名称上存在普通符号链接、但该链接不代表真实占用”的合法输入固定成必须拒绝；这与已批准计划“内部名称编码不得扩大合法输入拒绝范围、普通内容占用内部名称时应改用其他内部名称”的约定冲突。
- 本版不修改正式需求、不修改已批准执行计划、不降低任何 PASS 条件，也不修改 `ABSOLUTE_PASS`。41 个必需方法名称与数量不变；只扩展既有 R2/R3 合法输入 proof，并修正实现测试对“真实占用”和“普通同名符号链接”的区分。
- 本文件及同一提交的 `.apm/skills/professor-contact/tests/test_issue74_fixture_support.py`、`.apm/skills/professor-contact/tests/test_issue74_cross_run_claims.py`、`test-plan/issue-74-required-cases.json`、`test-plan/issue-74-pass-check.jq` 构成当前唯一权威测试方案正文。判定检查样例仍为 `test-plan/issue-74-check-samples.jq`、`test-plan/check-issue-74-pass-check.sh` 和 `.apm/skills/professor-contact/tests/issue74_recipe_checks.py`。
- 本版全部取代第六版 `issue74-test-r6`。历史方案和历史执行证据只作为来源记录，不需要执行者拼接。
- 正式需求：第 74 号议题需求第 1 版，R1—R4。
- 正式执行计划：`plan/issue-74.md` 第 3 版，提交 `a328e788a21af8fc7d3ebf052c399054d242b786`，已有正式批准。本次 Recipe 修订不重开计划审核。
- 兼容基准：`768b49ef4514e36edec6b57ed3821a99af9e9c00`。
- 判定语义保持 `ABSOLUTE_PASS`：正式 G74 中任何有效测试失败、错误、跳过、非零回归退出或总 `verdict != PASS` 都使 G74 为 `FAIL`。基线失败、范围外归属或“不是本 PR 引入”都不能把该次 G74 改写为 `PASS`。

## 第七版合法重开事实

本次只重开 R2/R3“内部占用编码不能扩大合法输入拒绝范围”的 proof，满足 `Test Engineer Rule` §6.2 的三项事实：

1. **冻结要求／规则**：第三版批准计划要求允许收紧的旧输入仅限已冻结危险类别和真实并发占用冲突；其他合法输入不得借内部占用编码扩大拒绝范围。占用名称编码属于内部实现，普通内容占住首选内部名称时应改用其他内部名称；只有真实活动或异常遗留占用才属于必须拒绝的占用冲突。
2. **负责 Proof／Case**：第六版 R2/R3 的负责方法是 `test_issue74_cross_run_claims.Issue74CrossRunClaimTests.test_claim_like_paths_without_live_claim_remain_legal`；同时 G74 使用 `--pattern 'test_*.py'` 执行整个生产者测试目录，因此 `test_fixture_support.py` 中任何未经正式要求支持的失败预期也会直接改变 `ABSOLUTE_PASS` verdict。
3. **最小错误结果**：没有活动占用时，在某合法根的首选内部锚点位置预先放置一个普通符号链接，链接目标是普通空目录且不带当前占用标记。该输入没有生产者归属、非空根、已有输出、根重合或真实并发占用。当前实现与新增实现测试仍把它当成真实占用而拒绝，因此正确实现若按计划将它作为普通内容并回退到下一个内部名称，旧 Recipe 反而会给出 `FAIL`，形成明确 `false-FAIL`。

修复方式固定如下：既有正式方法 `test_claim_like_paths_without_live_claim_remain_legal` 增加“普通符号链接占用当前首选内部锚点名”这一合法面，第 53、55 号两个受支持入口都必须成功，普通符号链接及其目标保持不变；`test_fixture_support.py` 中真实占用模拟必须携带当前内部占用标记，普通同名符号链接改为成功预期。方法总数仍为 41 个，不新增第二个 proof owner。

## 要求与证明归属

所有路径均相对于 `.apm/skills/professor-contact/`。

| 要求／证明 | 唯一负责者 | 直接证明 |
| --- | --- | --- |
| R2 成功结果兼容 | `test_issue74_fixture_support.Issue74FixtureTests.test_compatibility_bytes_manifest_hashes_and_returns` | 固定基准与当前版本的返回对象、文件字节、摘要和包装行为兼容 |
| R2 两种既有调用方式 | `test_cli_from_unrelated_directory_without_pythonpath` | 按文件加载和无关目录直接 CLI 均保持原约定 |
| R2/R3 内部占用名称不能扩大合法输入拒绝范围 | `test_issue74_cross_run_claims.Issue74CrossRunClaimTests.test_claim_like_paths_without_live_claim_remain_legal` | 无实际占用时四种 claim 风格路径，以及普通符号链接占用当前首选内部锚点名，均保持合法 |
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

第六版已经冻结的独立检出环境继续原样有效：从当前干净仓库通过本地 Git 对象建立一个位于系统临时目录下的独立检出，并在该检出中运行冻结命令。本版只改变一个 producer-local 合法输入断言，不改变该环境前提、结构化证据格式或判定程序。

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

P74 继续使用既有的判定通道验证和完整性样例。若以下文件相对已通过的第六版 Gate 2 来源均未改变，可记录 `REUSE_PRIOR_PASS`，并保存准确来源提交和影响分析：

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
2. 占用生成、冲突、释放和归属符合已批准计划：相同真实路径竞争同一占用；其他运行仍持有或异常遗留的实际占用不能被接管；未取得占用者不能清理他人状态；占用不能进入另一运行的样例或清单；内部占用名称编码不能在没有实际占用或其他冻结危险条件时永久禁用普通路径。
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

第六版当前有效运行 `issue74-evidence.Vf9dEgan` 保持其原始事实：909 个方法有效运行，41 个必需方法和整轮 `ABSOLUTE_PASS` 均通过。该运行证明的是第六版 Recipe 与当时测试输入；本版改变了 R2/R3 合法输入断言和 `test_fixture_support.py` 的正式全量回归输入，因此该运行不能作为第七版 G74 的当前 PASS 来源，也不能把旧 909 个结果重新判读为本版新增输入已经执行。

第七版 G74 选择 `EXECUTE_CURRENT`：产品修复后必须按上述独立检出 Recipe 重新执行一次完整回归。P74 的判定入口和通道验证若未变化，可按准确来源继续 `REUSE_PRIOR_PASS`；S74 按当前产品源码重新判断。

## Gate 3 记录要求

Gate 3 对每个必需 proof 记录：

- Requirement／Proof／Case ID；
- `EXECUTE_CURRENT`、`REUSE_PRIOR_PASS` 或 `REJUDGE_PRIOR_EVIDENCE`；
- 准确产品、Recipe、判定和证据版本；
- 原始证据位置、运行编号和命令；
- 影响分析及最终 verdict。

第七版 G74 固定为 `EXECUTE_CURRENT`。只有三个 Gate 均为 `PASS`、S74 满足、G74 满足上述 `ABSOLUTE_PASS`、41 个必需方法对当前产品版本均有有效 PASS，且没有未解决的 producer `FAIL` 或必需 case 的非通过终态，才能记录：

`Merge conclusion: READY`

在新的正式 G74 完成前：

`Gate 3: NOT_READY`

`Merge conclusion: NOT_READY`