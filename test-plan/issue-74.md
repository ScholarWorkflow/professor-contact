# 第 74 号议题测试方案：计划第 4 版对应第 2 版

## 版本与唯一来源

- 当前唯一修订：`issue74-plan4-test-r2`。
- 正式需求：Issue #74 需求第 1 版 R1–R4，正文读取版本更新时间 `2026-10-02T16:02:24Z`。
- 正式执行计划：`plan/issue-74.md` 计划第 4 版修订 1，语义修订提交 `07f895e3bfb91f2d27300042676aff5317d348cf`；PR 评论 `5971365538` 已给出 `Plan conclusion: APPROVED`。
- 兼容基准：`768b49ef4514e36edec6b57ed3821a99af9e9c00`。
- 产品实现基点：`bf0e59bc5aa989c8fcb1341d94ea44bfedc22127`。
- 本文件取代 `issue74-plan4-test-r1`；执行者只读取本文件和当前 HEAD 中列明的测试源码，不拼接旧 Recipe、旧结果或旧评论形成判定条件。
- 正式执行绑定执行时准确 `HEAD`，并记录本文件、`gate2_evidence.py`、Python 和 `jq` 的实际版本。

### 第 2 版重开原因

第 1 版存在满足 `Test Engineer Rule` §6.2 的明确 `false-PASS`：

1. 冻结要求：R2 要求第 53、55 号迁移后生成文件内容、摘要、返回对象保持兼容。
2. 负责证明：第 1 版 `T74-CLI`、`T74-53`、`T74-55`。
3. 最小错误实现：例如只修改第 53 号 profile 中 `大学：Fixture University` 这一行，当前构建器会同步生成新的 hash；第 1 版原有断言仍可能全部通过，但生成文件字节已经违反 R2。

第 2 版因此在 `test_issue74_cli_compat.py` 增加兼容基准对照：在同一组实际路径上分别运行 `768b49e...` 基准构建器与当前构建器，逐字节比较全部生成文件，并比较返回 manifest 与其中摘要。普通浅克隆没有基准对象时该单项测试允许 skip；正式 Recipe 在任何 Case 开始前强制验证基准提交可读，所以正式 `T74-CLI` 不允许靠该 skip 通过。

## 冻结要求

| Requirement | 冻结要求 |
| --- | --- |
| R1 | 共用工具保留在 `.apm/skills/professor-contact/tests/`，只用于测试并使用虚构数据。 |
| R2 | 抽取第 53、55 号准备入口重复的空目录准备、文件写入、摘要计算；两个既有入口实际复用；原命令参数、返回对象、错误类型、生成文件内容、摘要及各自验收要求保持兼容。 |
| R3 | 拒绝生产者检出目录及子目录、非目录目标、已有内容目标；拒绝时不覆盖或删除原有文件；不同正式运行使用独立目录；共用工具不启动浏览器、外部服务或代理，不修改业务程序。跨运行目录分配的唯一责任方是测试执行层。 |
| R4 | 仓库说明区分共用准备工具、既有执行判定入口、问题专属样例和断言，并说明新增样例及执行方法；正式判定复用 `gate2_evidence.py` 结构化结果；产品断言失败不能当成准备失败，空执行不能通过。 |

计划第 4 版修订 1 另冻结：第 53 号两根仅在解析后完全相同时拒绝；合法父子嵌套不能只因父子关系失败；第二根准备失败时只允许删除本次创建且目录身份仍一致的第一根。

## 证明分工

| Case | Requirement | 直接证明 |
| --- | --- | --- |
| `T74-CORE` | R2、R3 | `test_fixture_support.py`：共用 JSON 字节格式、SHA-256、危险目录拒绝、已有空目录身份保持、清单排他创建、第 53 号相等/嵌套与安全回滚、第 55 号清单写入。 |
| `T74-CLI` | R2 | `test_issue74_cli_compat.py`：两个脚本从无关工作目录、无 `PYTHONPATH` 按原 CLI 成功；当前返回 manifest 字段保持兼容；当前与 `768b49e...` 在相同路径输入下的返回对象、全部生成文件字节和摘要完全一致。 |
| `T74-53` | R1、R2、R3 | `test_issue53_stage4_runtime_assets.py`：第 53 号既有真实调用方验收继续成立。 |
| `T74-55` | R1、R2、R3 | `test_issue55_stage3_runtime_assets.py`：第 55 号既有真实调用方验收继续成立。 |
| `T74-STATIC` | R1、R2、R3、R4 | `test_issue74_static_acceptance.py`：PR 差异范围、两个入口真实复用同一个 helper、CLI 参数不漂移、helper 不引入浏览器/外部服务进程依赖、虚构数据标志和 README 责任说明。 |
| `T74-EVIDENCE` | R4 | `test_gate2_evidence.py`：当前判定入口能区分有效 PASS、产品 FAIL、准备/证据无效和零执行等终态；后续 cleanup 无效不能覆盖产品 FAIL。 |
| `RUN74` | R3 | 正式执行每次创建新的独占 `<run-root>` 和独立检出；本次所有可写测试状态位于该运行目录。 |

六个测试 Case 各执行一次对应文件；不运行与第 74 号无关的仓库测试作为本议题合并门槛。

## Gate 2 执行前检查

- `Executable`：六个 Case、`gate2_evidence.py`、Git、CPython 3.12 和 `jq` 构成完整命令链。仓库 CI 使用 Python 3.12，本方案固定 `python3.12`，失败后不得换解释器寻找 PASS。
- `Isolated`：测试内部使用临时目录；正式执行另外创建独占 `<run-root>`，并从当前干净来源仓库按准确 HEAD 创建独立 Git 检出。不同正式运行不得复用同一 `<run-root>`。
- `Observable`：每个 Case 的正式 verdict 只读取对应 `gate2_evidence.py` JSON 的 `.verdict`；`started`、`completed`、`events`、`failures`、`errors`、`skipped`、`missing_required_prefixes`、`interruption` 用于审计，不从日志关键词推断。
- `Discriminating`：`T74-EVIDENCE` 已覆盖成功、产品失败、准备无效、产品失败后 cleanup 无效、零执行、缺失执行、跳过与中断等通道。

本任务不依赖真实安装、代理委派、MCP、浏览器、外部服务、端口或用户 profile，因此不需要额外 runtime 业务 Preflight。

`test_issue74_static_acceptance.py` 在普通浅克隆中若读不到兼容基准，会只跳过“PR 差异范围”这一非正式检查；正式执行前置条件必须先成功执行 `git cat-file -e 768b49e...^{commit}`，因此正式 `T74-STATIC` 不允许出现该 skip。

临时 `.github/workflows/issue-74-formal.yml` 只提供具备 Python 3.12 的执行宿主，必须逐条执行本文件命令；它不是第二份验收要求或判定来源。正式 verdict 仍只来自下面的 Recipe 与 `gate2_evidence.py`。

## 正式执行前置

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
python3.12 --version > "$RUN_ROOT/python-version.txt" 2>&1
jq --version > "$RUN_ROOT/jq-version.txt"
git -C "$CHECKOUT" log -1 --format=%H -- test-plan/issue-74.md > "$RUN_ROOT/recipe-sha.txt"
git -C "$CHECKOUT" log -1 --format=%H -- \
  .apm/skills/professor-contact/tests/gate2_evidence.py \
  .apm/skills/professor-contact/tests/test_gate2_evidence.py \
  > "$RUN_ROOT/evaluator-sha.txt"

export TMPDIR="$RUN_ROOT/tmp"
export PYTHONDONTWRITEBYTECODE=1
cd "$CHECKOUT/.apm/skills/professor-contact"
```

若上述前置在任何 Case 开始前失败，尚未执行的 Case 为 `CASE_NOT_STARTED`；保存原始错误并停止，不换 Python、不退回来源工作树执行。

## 六个正式 Case

固定包装函数只保存原始退出码，不解释 verdict：

```sh
run_case() {
  case_id=$1
  pattern=$2
  prefix=$3
  set +e
  python3.12 tests/gate2_evidence.py \
    --start tests \
    --pattern "$pattern" \
    --require-prefix "$prefix" \
    --out "$RUN_ROOT/$case_id.json" \
    > "$RUN_ROOT/$case_id.stdout" \
    2> "$RUN_ROOT/$case_id.stderr"
  rc=$?
  set -e
  printf '%s\n' "$rc" > "$RUN_ROOT/$case_id-exit.txt"
}

run_case T74-CORE \
  test_fixture_support.py \
  test_fixture_support.

run_case T74-CLI \
  test_issue74_cli_compat.py \
  test_issue74_cli_compat.Issue74CliCompatibilityTests.

run_case T74-53 \
  test_issue53_stage4_runtime_assets.py \
  test_issue53_stage4_runtime_assets.Issue53Stage4RuntimeAssetTests.

run_case T74-55 \
  test_issue55_stage3_runtime_assets.py \
  test_issue55_stage3_runtime_assets.Issue55Stage3RuntimeAssetTests.

run_case T74-STATIC \
  test_issue74_static_acceptance.py \
  test_issue74_static_acceptance.Issue74StaticAcceptanceTests.

run_case T74-EVIDENCE \
  test_gate2_evidence.py \
  test_gate2_evidence.Gate2EvidenceTests.
```

每个 Case 的输出路径在同一运行中只能创建一次。某个 Case 非 `PASS` 后仍执行不依赖它的其他 Case，以一次得到全部可独立判断结果；不得删除证据后重跑失败 Case。

## 判定与证据

每个 Case 的正式 verdict 直接采用对应 JSON 的 `.verdict`：

- 有效成功 → `PASS`，且进程退出码必须为 0；
- 有效产品断言失败 → `FAIL`；
- 启动、准备、证据或执行无效 → 保留 `CASE_NOT_STARTED`、`INVALID_TEST_EXECUTION`、`NOT TESTED` 等原终态。

若 JSON 缺失/损坏，或 `.verdict == "PASS"` 但退出码不为 0，该 Case 为 `INVALID_TEST_EXECUTION`。产品 `FAIL` 不得被后续 cleanup 或一致性检查改写为 invalid。

```sh
for case in T74-CORE T74-CLI T74-53 T74-55 T74-STATIC T74-EVIDENCE; do
  jq '{schema_version,python,selection,tests_run,started,completed,missing_required_prefixes,load_errors,interruption,events,failures,errors,skipped,expected_failures,unexpected_successes,verdict}' \
    "$RUN_ROOT/$case.json"
done

test -z "$(git -C "$CHECKOUT" status --porcelain)"
```

完整 JSON/stdout/stderr 留在执行环境；仓库只保存最小脱敏结果记录 `test-plan/issue-74-results.md`。结构化证据可保存在 GitHub Actions artifact；不得提交完整临时运行目录。

## Gate 3 决策

本版首次正式判断中，六个 Case 全部选择 `EXECUTE_CURRENT`。只有满足以下全部条件，Gate 3 才可为 `PASS`：

- `T74-CORE`、`T74-CLI`、`T74-53`、`T74-55`、`T74-STATIC`、`T74-EVIDENCE` 对当前版本均为有效 `PASS`，且对应退出码均为 0；
- 六个 required prefix 均实际启动；
- `T74-CLI` 的兼容基准逐字节比较没有 skip；
- 正式独立检出执行后仍干净；
- 没有未解决 `PRODUCT`、`RECIPE` 或执行偏离问题。

旧计划第 3 版结果、普通 CI 成功、测试方案通过均不能替代本版 Gate 3。

## Gate 2 完整性检查

首次形成本版 `PASS + COMPLETE` 前必须确认：R1–R4 每个独立 claim 有明确 owner；第 53 号相等/嵌套/回滚与批准计划一致；六个 Case 是最小定向执行且没有重复业务运行；CLI、返回对象及基准逐字节兼容有直接证明；差异范围、真实 helper 复用和 README 说明由 `T74-STATIC` 证明；判定通道由 `T74-EVIDENCE` 验证；正式 verdict 可由固定 JSON 唯一得出。
