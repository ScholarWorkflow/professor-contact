# 第 74 号议题测试方案：计划第 4 版对应第 1 版

## 状态与唯一来源

- 修订号：`issue74-plan4-test-r1`。
- 正式需求：Issue #74 需求第 1 版 R1–R4，正文读取版本更新时间 `2026-10-02T16:02:24Z`。
- 正式执行计划：`plan/issue-74.md` 计划第 4 版修订 1，语义修订提交 `07f895e3bfb91f2d27300042676aff5317d348cf`；PR 评论 `5971365538` 已给出 `Plan conclusion: APPROVED`。
- 兼容基准：`768b49ef4514e36edec6b57ed3821a99af9e9c00`。
- 被审产品实现基点：`bf0e59bc5aa989c8fcb1341d94ea44bfedc22127`。其后的测试工程师提交只允许增加或修改 `test-plan/issue-74*` 与 `.apm/skills/professor-contact/tests/test_issue74_cli_compat.py`；S74 必须确认没有额外业务程序差异。
- 当前唯一权威测试方案由本文件、`test-plan/issue-74-required-cases.json`、`test-plan/issue-74-static-check.py` 与 `.apm/skills/professor-contact/tests/test_issue74_cli_compat.py` 共同组成。
- 计划第 4 版已明确删除旧测试方案、旧执行结果和旧专属审核脚本；此前针对计划第 3 版形成的 `issue74-test-r*`、执行记录和 Gate 2/Gate 3 结论均不作为本版 PASS 来源。
- 正式运行绑定执行时准确 `HEAD`，并记录当前方案与判定程序版本。
- 当前状态：等待 Gate 2 完整复审；Gate 2 通过前不得开始本版正式验收执行。

## 冻结要求

本方案只证明 Issue #74 需求第 1 版与计划第 4 版修订 1 已批准的行为，不新增产品要求。

| Requirement | 冻结要求 |
| --- | --- |
| R1 | 共用工具保留在 `.apm/skills/professor-contact/tests/`，只用于测试并使用虚构数据。 |
| R2 | 抽取第 53、55 号准备入口重复的空目录准备、文件写入、摘要计算；两个既有入口实际复用；原命令参数、返回对象、错误类型、生成文件内容、摘要及各自验收要求保持兼容。 |
| R3 | 拒绝生产者检出目录及子目录、非目录目标、已有内容目标；拒绝时不覆盖或删除原有文件；不同正式运行使用独立目录；共用工具不启动浏览器、外部服务或代理，不修改业务程序。计划第 4 版把跨运行目录分配的唯一责任方冻结为测试执行层。 |
| R4 | 仓库内说明区分共用准备工具、既有执行判定入口、问题专属样例和断言，并说明新增样例及执行测试方法；正式执行复用 `gate2_evidence.py` 结构化结果；产品断言失败不能当成准备失败，空执行不能通过。 |

计划第 4 版同时冻结：第 53 号两根仅在解析后完全相同时拒绝；合法父子嵌套不能只因父子关系失败；第 53 号第二根准备失败时只允许删除本次创建且目录身份仍一致的第一根。

## 要求到证明的唯一归属

| Proof ID | Requirement | 负责证明 | 不证明 |
| --- | --- | --- | --- |
| `T74-CORE` | R2、R3 | `test_fixture_support.py` 当前 16 个方法：共用写入/摘要格式、危险路径拒绝、已有空目录身份保持、清单排他创建、第 53 号相等/嵌套语义、回滚边界、第 55 号清单字节 | 不证明 README 文案与 PR 差异范围 |
| `T74-CLI` | R2 | `test_issue74_cli_compat.py` 当前 1 个方法：第 53、55 号脚本都从无关工作目录、无 `PYTHONPATH` 的受支持 CLI 入口成功运行并生成对应清单 | 不证明业务阶段运行时路由 |
| `T74-53` | R1、R2、R3 | `test_issue53_stage4_runtime_assets.py` 当前 8 个既有验收方法，证明第 53 号真实调用方仍能使用迁移后的准备入口，且其原有验收断言保持成立 | 不证明第 55 号入口 |
| `T74-55` | R1、R2、R3 | `test_issue55_stage3_runtime_assets.py` 当前 16 个既有验收方法，证明第 55 号真实调用方仍能使用迁移后的准备入口，且其原有验收断言保持成立 | 不证明第 53 号双根回滚 |
| `T74-EVIDENCE` | R4 | `test_gate2_evidence.py` 当前 4 个方法，区分 PASS、产品 FAIL、准备/环境无效、产品失败后清理无效、空执行/缺失执行等通道 | 不证明产品准备入口本身正确 |
| `S74` | R1、R2、R3、R4 | `issue-74-static-check.py`：差异范围、共用 helper 外部依赖边界、两个入口真实复用、CLI 参数、虚构标志、README 必需说明 | 不替代运行时产品断言 |
| `RUN74` | R3 | 正式执行环境每次新建独占 `<run-root>` 和独立检出；本次运行所有临时写入位于该 `<run-root>` | 不要求 `fixture_support.py` 自己分配或仲裁不同运行目录 |

`test-plan/issue-74-required-cases.json` 固定五个运行 proof 的当前模块前缀与方法数量：`T74-CORE=16`、`T74-CLI=1`、`T74-53=8`、`T74-55=16`、`T74-EVIDENCE=4`。这些数量用于确认当前冻结 proof 没有缺失，不把整个仓库总测试数量写成产品要求。

## Gate 2 执行前检查

本次 Merge Gate 不依赖真实安装、代理委派、MCP、浏览器、外部服务、端口、用户 profile 或第三方运行时。五个动态 proof 都是生产者仓库内的确定性测试；S74 是确定性源码/文档检查。因此不需要 Runtime Preflight 的真实外部运行。

对完整证明链的四项检查如下：

- `Executable`：`gate2_evidence.py`、五个 proof 文件及 S74 检查器均存在；相关测试只使用仓库代码、Python 标准库和临时目录。正式运行使用新的独立 Git 检出，不依赖调用者工作树文件。仓库 CI 明确固定 CPython 3.12，本方案同样固定 `python3.12`，不允许失败后换解释器。
- `Isolated`：动态测试使用 `TemporaryDirectory`；正式执行另外创建本次独占 `<run-root>`，并把 `TMPDIR` 指向该目录。不同正式运行必须重新创建新的 `<run-root>`，不得复用旧运行目录。
- `Observable`：动态 proof 的正式事实直接来自 `gate2_evidence.py` JSON 的 `started`、`completed`、`events`、`failures`、`errors`、`skipped`、`missing_required_prefixes`、`interruption`、`verdict`；S74 输出独立 JSON。
- `Discriminating`：`T74-EVIDENCE` 明确包含合法成功、产品断言失败、fixture/prerequisite 失败、产品失败后 cleanup 失败、零执行、缺失必需 proof、跳过和中断反例；不会把产品 FAIL 改成准备失败，也不会把无执行改成 PASS。

没有发现需要在 Gate 2 前先运行正式验收才能确认的证据能力缺口。

## 正式执行环境

正式执行只允许从当前干净来源仓库创建一次新的独立检出。`SOURCE_REPO` 只提供 Git 对象；正式测试不得从来源工作树读取产品文件。

```sh
set -eu
SOURCE_REPO=$(git rev-parse --show-toplevel)
SOURCE_SHA=$(git -C "$SOURCE_REPO" rev-parse HEAD)
BASE_SHA=768b49ef4514e36edec6b57ed3821a99af9e9c00

command -v python3.12 >/dev/null
command -v jq >/dev/null
test -z "$(git -C "$SOURCE_REPO" status --porcelain)" || exit 2
git -C "$SOURCE_REPO" cat-file -e "$BASE_SHA^{commit}" || exit 2

RUN_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/issue74-plan4.XXXXXXXX")
CHECKOUT="$RUN_ROOT/checkout"
mkdir -p "$RUN_ROOT/tmp"

git clone --no-local --no-checkout "$SOURCE_REPO" "$CHECKOUT"
git -C "$CHECKOUT" checkout --detach "$SOURCE_SHA"
test "$(git -C "$CHECKOUT" rev-parse HEAD)" = "$SOURCE_SHA" || exit 2
test -z "$(git -C "$CHECKOUT" status --porcelain)" || exit 2
git -C "$CHECKOUT" cat-file -e "$BASE_SHA^{commit}" || exit 2

printf '%s\n' "$SOURCE_SHA" > "$RUN_ROOT/product-sha.txt"
printf '%s\n' "$CHECKOUT" > "$RUN_ROOT/checkout-path.txt"
python3.12 --version > "$RUN_ROOT/python-version.txt" 2>&1
jq --version > "$RUN_ROOT/jq-version.txt"

git -C "$CHECKOUT" log -1 --format=%H -- \
  test-plan/issue-74.md \
  test-plan/issue-74-required-cases.json \
  test-plan/issue-74-static-check.py \
  .apm/skills/professor-contact/tests/test_issue74_cli_compat.py \
  > "$RUN_ROOT/recipe-sha.txt"
git -C "$CHECKOUT" log -1 --format=%H -- \
  .apm/skills/professor-contact/tests/gate2_evidence.py \
  > "$RUN_ROOT/evaluator-sha.txt"

export TMPDIR="$RUN_ROOT/tmp"
export PYTHONDONTWRITEBYTECODE=1
cd "$CHECKOUT/.apm/skills/professor-contact"
```

若 `python3.12`、`jq`、Git、基准提交或独立检出前提不可用，或来源仓库/独立检出不干净、检出 SHA 不一致，则 `CASE_NOT_STARTED`；保存原始错误后停止，不换 Python、不退回来源工作树继续执行。

## G74：完整生产者回归与必需 proof

### 身份与依据

- Case ID：`G74`。
- Requirement：R1–R4；动态部分由 `T74-CORE`、`T74-CLI`、`T74-53`、`T74-55`、`T74-EVIDENCE` 分工。
- 判定语义：`ABSOLUTE_PASS`。当前有效执行中任一正式失败、错误、跳过、加载错误、中断、缺少必需 proof 或总 `verdict != PASS`，G74 即不通过；不得用基线也失败、范围外归属或 CI 通过抵消。
- `CASE_STARTED`：`gate2_evidence.py` 成功加载测试且首个测试进入 `started` 后。

### Recipe

在上节独立检出的 `.apm/skills/professor-contact` 目录执行一次：

```sh
set +e
python3.12 tests/gate2_evidence.py \
  --start tests \
  --pattern 'test_*.py' \
  --require-prefix test_fixture_support. \
  --require-prefix test_issue74_cli_compat.Issue74CliCompatibilityTests. \
  --require-prefix test_issue53_stage4_runtime_assets.Issue53Stage4RuntimeAssetTests. \
  --require-prefix test_issue55_stage3_runtime_assets.Issue55Stage3RuntimeAssetTests. \
  --require-prefix test_gate2_evidence.Gate2EvidenceTests. \
  --out "$RUN_ROOT/g74.json" \
  > "$RUN_ROOT/g74.stdout" \
  2> "$RUN_ROOT/g74.stderr"
G74_EXIT=$?
printf '%s\n' "$G74_EXIT" > "$RUN_ROOT/g74-exit.txt"
set -e
```

然后只按 JSON 字段判定：

```sh
test "$(cat "$RUN_ROOT/g74-exit.txt")" = 0

jq -e '
  .verdict == "PASS"
  and .load_errors == []
  and .interruption == null
  and .started == .completed
  and (.started | length) == .tests_run
  and (.started | unique | length) == .tests_run
  and .events == []
  and .failures == []
  and .errors == []
  and .skipped == []
  and .expected_failures == []
  and .unexpected_successes == []
  and .missing_required_prefixes == []
' "$RUN_ROOT/g74.json"

jq -e \
  --slurpfile required "$CHECKOUT/test-plan/issue-74-required-cases.json" '
  . as $e
  | ($required[0].cases | all(
      . as $case
      | ([ $e.started[] | select(startswith($case.required_prefix)) ] | length)
          == $case.expected_count
    ))
' "$RUN_ROOT/g74.json"

test -z "$(git -C "$CHECKOUT" status --porcelain)"
```

两个 `jq -e` 均为真、`G74_EXIT=0` 且运行后独立检出仍干净时，G74 唯一 verdict 为 `PASS`。`gate2_evidence.py` 已把产品断言失败记录为 `FAIL`，把准备/环境问题记录为 `INVALID_TEST_EXECUTION` 或启动前终态；执行者不得重新解释。

## S74：静态范围、复用、CLI 与文档证明

### 身份与依据

- Case ID：`S74`。
- Requirement：R1、R2、R3、R4。
- Proof：确认最终差异未修改业务程序；共用 helper 没有浏览器/外部服务进程依赖；第 53、55 号入口真实复用同一个 helper 的错误类型、JSON 写入和 SHA-256；原 CLI 参数不变；fixture 保持虚构标志；README 包含 R4 与计划第 4 版的目录 owner 说明。

### Recipe

在同一个独立 `CHECKOUT` 执行：

```sh
set +e
python3.12 "$CHECKOUT/test-plan/issue-74-static-check.py" \
  > "$RUN_ROOT/s74.json" \
  2> "$RUN_ROOT/s74.stderr"
S74_EXIT=$?
printf '%s\n' "$S74_EXIT" > "$RUN_ROOT/s74-exit.txt"
set -e

test "$(cat "$RUN_ROOT/s74-exit.txt")" = 0
jq -e '.verdict == "PASS" and (.checks | length) > 0 and (.error? == null)' \
  "$RUN_ROOT/s74.json"
test -z "$(git -C "$CHECKOUT" status --porcelain)"
```

退出码为 0、JSON `verdict` 为 `PASS` 且独立检出仍干净时，S74 唯一 verdict 为 `PASS`。

## 执行、重试与证据保存

- G74 与 S74 各执行一次，不因结果不理想重试，不修改输入、测试、判定条件或 Python 版本来寻找 PASS。
- 若在 `CASE_STARTED` 前出现 Git、Python、`jq`、文件系统等合法执行前提阻断，记录 `CASE_NOT_STARTED`；开始后测试基础设施或证据损坏按 `gate2_evidence.py` 结构化结果归类。产品断言失败保持 `FAIL`。
- 不复用计划第 3 版的任何第 74 号执行结果。本版首次 Gate 3 对 G74、S74 都选择 `EXECUTE_CURRENT`。
- 完整 stdout/stderr、运行目录和完整 JSON 保留在本地。仓库只提交最小脱敏证据：产品 SHA、运行编号、实际 Python/`jq` 版本、G74 关键结构化字段、五个必需 proof 的方法数量、S74 检查结果和最终 verdict；不得提交整个临时运行目录。
- 正式结果写入 `test-plan/issue-74-results.md`；若提交结构化证据副本，路径固定为 `test-plan/evidence/issue-74/`，删除调用者机器无关的绝对路径后再提交。

## Gate 3 决策表

| Case | 首次本版动作 | PASS 条件 |
| --- | --- | --- |
| G74 | `EXECUTE_CURRENT` | `ABSOLUTE_PASS` 条件全部满足，且五个冻结 proof 的当前方法数量分别为 16/1/8/16/4 |
| S74 | `EXECUTE_CURRENT` | 静态检查退出码 0，JSON `verdict=PASS`，运行后检出干净 |

只有 G74、S74 都对当前 HEAD 有有效 PASS，且没有新的未解决 `PRODUCT`、`RECIPE` 或执行偏离问题，第三关口才可为 `PASS`。Gate 2 通过本身不等于第三关口通过。

## Gate 2 完整性检查清单

首次形成 `PASS + COMPLETE` 前，审核者必须确认：

1. R1–R4 均有唯一 proof owner；没有把旧计划第 3 版的占用/锚点设计重新带入本版要求。
2. 第 53 号嵌套合法、完全相同拒绝、第二根失败回滚三项与计划第 4 版修订 1 一致。
3. G74 使用单次完整回归，没有为了同一产品事实重复运行相同业务入口；S74 只负责源码/文档事实。
4. `gate2_evidence.py` 的 JSON 字段、`jq` 判定和五个 proof 数量共同给出唯一 verdict。
5. 第 53、55 号受支持 CLI 从无关工作目录、无 `PYTHONPATH` 的直接调用由 `T74-CLI` 明确证明，不靠模块导入成功间接推断。
6. 不需要真实安装、代理、MCP、浏览器、外部服务或用户状态；不存在未处理的 Runtime Preflight 假设。
7. 不允许旧测试方案、旧执行结果、普通 CI 成功代替本版正式 G74/S74。

本文件创建时不自行声明 Gate 2 已通过；正式 Gate 2 结论由测试工程师在完整复审后单独记录。
