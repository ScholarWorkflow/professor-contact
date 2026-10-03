# 第 74 号议题测试方案：计划第 4 版对应第 1 版

## 状态与唯一来源

- 修订号：`issue74-plan4-test-r1`。
- 正式需求：Issue #74 需求第 1 版 R1–R4，正文读取版本更新时间 `2026-10-02T16:02:24Z`。
- 正式执行计划：`plan/issue-74.md` 计划第 4 版修订 1，语义修订提交 `07f895e3bfb91f2d27300042676aff5317d348cf`；PR 评论 `5971365538` 已给出 `Plan conclusion: APPROVED`。
- 兼容基准：`768b49ef4514e36edec6b57ed3821a99af9e9c00`。
- 被审产品实现基点：`bf0e59bc5aa989c8fcb1341d94ea44bfedc22127`。其后的测试工程师提交只允许修改本文件，以及新增 `.apm/skills/professor-contact/tests/test_issue74_cli_compat.py`、`.apm/skills/professor-contact/tests/test_issue74_static_acceptance.py`；正式执行前须确认没有额外业务程序差异。
- 当前唯一权威测试方案是本文件指定的 proof、Recipe、判定条件和当前 HEAD 中对应测试源码；执行者不读取历史 amendment。
- 计划第 4 版已明确删除旧测试方案、旧执行结果和旧专属审核脚本；此前针对计划第 3 版形成的 `issue74-test-r*`、执行记录和 Gate 2/Gate 3 结论均不作为本版 PASS 来源。
- 正式运行绑定执行时准确 `HEAD`，并记录本文件与 `gate2_evidence.py` 的实际版本。
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
| `T74-CORE` | R2、R3 | `test_fixture_support.py`：共用写入/摘要格式、危险路径拒绝、已有空目录身份保持、清单排他创建、第 53 号相等/嵌套语义、回滚边界、第 55 号清单字节 | 不证明 README 文案与 PR 差异范围 |
| `T74-CLI` | R2 | `test_issue74_cli_compat.py`：第 53、55 号脚本都从无关工作目录、清掉 `PYTHONPATH` 后按原 CLI 入口成功运行；两个 `build_fixture` 返回对象保持基准字段集合，并与实际写出的 manifest 一致 | 不证明业务阶段运行时路由 |
| `T74-53` | R1、R2、R3 | `test_issue53_stage4_runtime_assets.py` 既有验收，证明第 53 号真实调用方仍能使用迁移后的准备入口，且原有验收断言保持成立 | 不证明第 55 号入口 |
| `T74-55` | R1、R2、R3 | `test_issue55_stage3_runtime_assets.py` 既有验收，证明第 55 号真实调用方仍能使用迁移后的准备入口，且原有验收断言保持成立 | 不证明第 53 号双根回滚 |
| `T74-STATIC` | R1、R2、R3、R4 | `test_issue74_static_acceptance.py`：差异范围、共用 helper 外部运行依赖边界、两个入口真实复用、CLI 参数、虚构标志、README 必需说明 | 不替代动态产品断言 |
| `T74-EVIDENCE` | R4 | `test_gate2_evidence.py`：验证 `gate2_evidence.py` 的 PASS、产品 FAIL、准备无效、空执行/缺失执行、跳过、中断等 verdict channel | 不证明产品准备入口本身正确 |
| `RUN74` | R3 | 正式执行每次新建独占 `<run-root>` 和独立检出；本次运行所有临时写入位于该 `<run-root>` | 不要求 `fixture_support.py` 自己分配或仲裁不同运行目录 |

所有动态 proof 在一次 G74 完整生产者回归中共同执行。不存在为同一业务事实重复启动第二次验收运行。

## Gate 2 执行前检查

本次 Merge Gate 不依赖真实安装、代理委派、MCP、浏览器、外部服务、端口、用户 profile 或第三方运行时。所有 proof 都是生产者仓库内的确定性测试，因此不需要 Runtime Preflight 的真实外部业务运行。

对完整证明链的四项检查如下：

- `Executable`：`gate2_evidence.py` 及上述 proof 文件均存在；测试只使用仓库代码、Python 标准库、Git 和临时目录。仓库 CI 固定 CPython 3.12，本方案同样固定 `python3.12`，失败后不得换解释器寻找 PASS。
- `Isolated`：动态测试使用 `TemporaryDirectory`；正式执行另外创建本次独占 `<run-root>`，把 `TMPDIR` 指向该目录，并在来源仓库及其 worktree 之外创建干净独立检出。不同正式运行必须重新创建新的 `<run-root>`。
- `Observable`：正式 verdict 直接读取 `gate2_evidence.py` JSON 的 `verdict`；`started`、`completed`、`events`、`failures`、`errors`、`skipped`、`missing_required_prefixes`、`interruption` 用于审计该 verdict，不从日志文本推断。
- `Discriminating`：`T74-EVIDENCE` 对当前 `gate2_evidence.py` 直接验证合法成功 → `PASS`、有效产品失败 → `FAIL`、准备/证据/执行无效 → invalid 类终态；同时覆盖“产品失败后 cleanup 失败不能把产品 FAIL 改写成 invalid”和“零执行不能 PASS”。

`T74-EVIDENCE` 与 `gate2_evidence.py` 在产品实现基点 `bf0e59b` 上已经由仓库 Python 3.12 CI 成功执行；这只作为 Gate 2 的判定程序能力依据，不作为本版产品验收 PASS。两文件自该基点后未修改时可继续作为 Preflight 依据；若任一文件在正式执行前变化，须先重新判断 Gate 2 受影响范围。

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

git -C "$CHECKOUT" log -1 --format=%H -- test-plan/issue-74.md \
  > "$RUN_ROOT/recipe-sha.txt"
git -C "$CHECKOUT" log -1 --format=%H -- \
  .apm/skills/professor-contact/tests/gate2_evidence.py \
  .apm/skills/professor-contact/tests/test_gate2_evidence.py \
  > "$RUN_ROOT/evaluator-sha.txt"

export TMPDIR="$RUN_ROOT/tmp"
export PYTHONDONTWRITEBYTECODE=1
cd "$CHECKOUT/.apm/skills/professor-contact"
```

若 `python3.12`、`jq`、Git、基准提交或独立检出前提不可用，或来源仓库/独立检出不干净、检出 SHA 不一致，则 G74 为 `CASE_NOT_STARTED`；保存原始错误后停止，不换 Python、不退回来源工作树继续执行。

## G74：一次正式完整回归

### 身份与依据

- Case ID：`G74`。
- Requirement：R1–R4；由 `T74-CORE`、`T74-CLI`、`T74-53`、`T74-55`、`T74-STATIC`、`T74-EVIDENCE` 分工。
- 判定语义：`ABSOLUTE_PASS`。当前有效执行中任一正式产品失败、错误、跳过、加载错误、中断、缺少必需 proof 或总 `verdict != PASS`，均不得写成 G74 `PASS`。
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
  --require-prefix test_issue74_static_acceptance.Issue74StaticAcceptanceTests. \
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

正式 verdict 直接采用 `g74.json.verdict`。退出码只做一致性检查：`PASS` 必须同时满足 `G74_EXIT=0`；任何非 `PASS` 必须保留 JSON 原终态，不能改写。若 JSON 缺失/损坏，或退出码与 `verdict` 的受支持关系冲突，则记 `INVALID_TEST_EXECUTION`。

读取结构化证据：

```sh
jq '{schema_version,python,selection,tests_run,started,completed,missing_required_prefixes,load_errors,interruption,events,failures,errors,skipped,expected_failures,unexpected_successes,verdict}' \
  "$RUN_ROOT/g74.json"

if [ "$(jq -r '.verdict' "$RUN_ROOT/g74.json")" = PASS ]; then
  test "$(cat "$RUN_ROOT/g74-exit.txt")" = 0
  jq -e '.missing_required_prefixes == [] and .load_errors == [] and .interruption == null' \
    "$RUN_ROOT/g74.json"
fi

test -z "$(git -C "$CHECKOUT" status --porcelain)"
```

`gate2_evidence.py` 的当前分类规则已经由 `T74-EVIDENCE` 验证；执行者不得用 stderr 文本、普通 CI、基线结果或“不是本 PR 引入”覆盖该结构化 verdict。

## 执行、重试与证据保存

- G74 正式执行一次，不因结果不理想重试，不修改输入、测试、判定条件或 Python 版本来寻找 PASS。
- 若在 `CASE_STARTED` 前出现 Git、Python、`jq`、文件系统等合法执行前提阻断，记录 `CASE_NOT_STARTED`；开始后准备/证据问题按 `gate2_evidence.py` 结构化结果归类。产品断言失败保持 `FAIL`。
- 不复用计划第 3 版的任何第 74 号执行结果。本版首次 Gate 3 对 G74 选择 `EXECUTE_CURRENT`。
- 完整 stdout/stderr、运行目录和完整 JSON 保留在本地。仓库只提交最小脱敏证据：产品 SHA、运行编号、实际 Python/`jq` 版本、G74 关键结构化字段、六个 required prefix 的存在情况和最终 verdict；不得提交整个临时运行目录。
- 正式结果写入 `test-plan/issue-74-results.md`；若提交结构化证据副本，路径固定为 `test-plan/evidence/issue-74/`，删除调用者机器无关的绝对路径后再提交。

## Gate 3 决策

| Case | 首次本版动作 | PASS 条件 |
| --- | --- | --- |
| G74 | `EXECUTE_CURRENT` | 当前 HEAD 在独立检出中按冻结命令得到 `g74.json.verdict == PASS`、`G74_EXIT=0`、六个 required prefix 全部存在，且执行后检出仍干净 |

只有 G74 对当前版本有有效 PASS，且没有新的未解决 `PRODUCT`、`RECIPE` 或执行偏离问题，第三关口才可为 `PASS`。Gate 2 通过本身不等于第三关口通过。

## Gate 2 完整性检查清单

首次形成 `PASS + COMPLETE` 前，审核者必须确认：

1. R1–R4 均有唯一 proof owner；没有把旧计划第 3 版的占用/锚点设计重新带入本版要求。
2. 第 53 号嵌套合法、完全相同拒绝、第二根失败回滚三项与计划第 4 版修订 1 一致。
3. G74 只运行一次完整生产者回归，没有为了同一产品事实重复启动第二次业务验收。
4. 第 53、55 号受支持 CLI 从无关工作目录、无 `PYTHONPATH` 的直接调用，以及两个 `build_fixture` 返回 manifest 合同，由 `T74-CLI` 明确证明，不靠模块导入成功间接推断。
5. 差异范围、真实 helper 复用、CLI 参数、虚构数据和 README 责任说明由 `T74-STATIC` 在同一次 G74 中证明。
6. 正式 verdict 只来自当前 `gate2_evidence.py`；其三个 verdict channel 与关键对抗样例由 `T74-EVIDENCE` 验证。
7. 不需要真实安装、代理、MCP、浏览器、外部服务或用户状态；不存在未处理的 Runtime Preflight 假设。
8. 不允许旧测试方案、旧执行结果、普通 CI 成功代替本版正式 G74。

本文件创建时不自行声明 Gate 2 已通过；正式 Gate 2 结论由测试工程师在完整复审后单独记录。
