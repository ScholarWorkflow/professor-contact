# 第67号问题第二关口单一权威测试方案第26版（待完成判定程序验证）

`Gate 2 revision: issue-67-gate2-r26-2026-10-04`

本版在用户授权修改后采用新的环境资产及会话配置，完整取代第25版及更早方案的执行正文；不拼接历史修订。本版尚未通过第二关口，禁止据此启动正式业务验收。发布评论固定本文件的不可变提交，执行前必须先完成第2节的受影响判定程序验证，再由测试工程师确认第二关口。

## 0. 限定重开、问题与当前输入

依据测试工程师规则第6.2节，本轮为输入变化后的限定修订审核。已核实上游测试夹具第33号拉取请求于2026-10-04 06:39:26 UTC合并，新固定输入为 `c738fa2f8bcbb16cd99d741332d5f59b062b6357`、`skills-test-fixtures/codex-eval-adapter@16`。第25版正式方案及实际执行仍固定 `a96c239cca0e1e07eb142089e4d379baf4072277`、第15版，并使用 `--ephemeral`。执行者遵守旧方案，不能将版本落后归责为执行偏离。

变化影响链：新版正式观察约定支持结构化创建调用、子代理活动及子线程来源联合归属；采用已获上游验证的持久会话、显式启用新版子代理协议，并用根级 `projects` 内联表表达信任目录。旧请求构造器与判定器固定临时会话及旧配置，不能原样接受本轮新输入。最小修改为第67号请求构造、实际请求记录、隔离判定器请求一致性检查、对应自检和本方案。分类为 `RECIPE`，上游能力属于 `HARNESS`；没有新增产品要求或产品缺陷。

第25版原始响应存在真实创建调用及同编号的线程存储失败；旧适配器没有形成正式归属，判定器在不可观察处提前返回，不能把48项前置检查通过写成全部业务字节检查通过。旧受阻尝试保留。尚未证明本版变更必然修复该故障。

当前输入：

- 需求：2026年9月29日逐教授状态要求及2026年10月1日独立合并澄清。
- 冻结约定：`issue-67-gate1-r3-2026-10-01`，`PASS`，12项要求。
- 正式计划：`issue-67-plan-r19-2026-10-02`，`APPROVED`。
- 产品基线：`a17aeb972aaa3ef2d1025d40de0d5bb93e3bcd69`；基准：`768b49ef4514e36edec6b57ed3821a99af9e9c00`。
- 当前产品／方案／判定程序目标提交：以本版发布评论记录的完整提交为准；运行前填入 `PRODUCER_SHA`，禁止以浮动分支代替。
- 环境资产：`c738fa2f8bcbb16cd99d741332d5f59b062b6357`，适配器第16版，干净检出。
- 公共模型与推理：项目共识2026-10-04 06:35 UTC版本，`gpt-6-luna`、`low`。
- 会话：默认持久会话，`features.multi_agent_v2.enabled=true`；禁止临时会话、恢复旧线程及消费者手工补丁。
- 本轮只修改测试资产；未运行测试、未启动代理、未修改产品或正式执行计划。

已读来源及读取时的可编辑评论更新时间（UTC）：

- [冻结约定](https://github.com/ScholarWorkflow/professor-contact/issues/67#issuecomment-5931970347)：2026-10-01 12:58:55。
- [正式计划](https://github.com/ScholarWorkflow/professor-contact/issues/67#issuecomment-5938921531)：2026-10-01 19:25:17；[批准](https://github.com/ScholarWorkflow/professor-contact/pull/71#issuecomment-5945944360)：2026-10-02 05:06:42。
- [第25版](https://github.com/ScholarWorkflow/professor-contact/issues/67#issuecomment-5977667426)：2026-10-04 07:22:32；[执行证据](https://github.com/ScholarWorkflow/professor-contact/pull/71#issuecomment-5977896820)：2026-10-04 07:57:35。
- [上游观察约定决定](https://github.com/RekiDunois/skills-test-fixtures/issues/32#issuecomment-5971924892)：2026-10-03 18:00:01；[持久会话实测](https://github.com/RekiDunois/skills-test-fixtures/issues/32#issuecomment-5973441714)：2026-10-03 21:01:10；[上游终审](https://github.com/RekiDunois/skills-test-fixtures/issues/32#issuecomment-5977270628)：2026-10-04 06:21:44。
- 本地当前项目共识、测试工程师规则；固定上游第16版完整合同、解析程序、接线说明及 `docs/issue-32-gate2.md`；当前拉取请求差异、请求及判定程序、已有原始证据均已读取。上游两级代理是否形成，不提升为本议题的额外验收要求。
- [命令参数官方说明](https://developers.openai.com/codex/cli/reference/)支持临时会话不保留会话记录；本轮采用上游已验证的持久会话入口。该依据不替代本议题业务执行。

受影响要求仅为 `R67-G1-2/4/5/9/12` 的 `PC67-RISO` 及其判定程序验证。第48、68号议题不成为合并前置条件。

## 1. 要求与证明负责者

| Gate 1 r3 | 当前负责证明 |
|---|---|
| `R67-G1-1` | `PC67-DSTATE` |
| `R67-G1-2` | `PC67-DSTATE` + `PC67-DADJ` + `PC67-RISO` + `PC67-RBIND` |
| `R67-G1-3` | `PC67-DSTATE` |
| `R67-G1-4` | `PC67-DSTATE` + `PC67-DADJ` + `PC67-RISO` |
| `R67-G1-5` | `PC67-DSTATE` + `PC67-RISO` |
| `R67-G1-6` | `PC67-DADJ` |
| `R67-G1-7` | `PC67-DADJ` |
| `R67-G1-8` | `PC67-DADJ` + `PC57-R2` |
| `R67-G1-9` | `PC67-DSTATE` + `PC67-RISO` |
| `R67-G1-10` | `PC67-DSTATE` + `PC67-DADJ` |
| `R67-G1-11` | `PC67-DSTATE` |
| `R67-G1-12` | `PC67-DADJ` + `PC67-RBIND` + `PC67-RISO` |

第48、68号问题不是第67号问题的合并前置条件。

## 2. 确定性证明与受影响判定程序验证

所有命令在固定的干净目标检出中顺序执行。回归判定语义为 `ABSOLUTE_PASS`：指定命令退出码0且每项测试通过；不能以失败数量相同抵消失败。记录命令、输入版本、日志和退出码。

```bash
: "${PRODUCER_REPO:?set exact producer checkout absolute path}"
: "${PRODUCER_SHA:?set full commit from the canonical r26 publication}"
test "$(git -C "$PRODUCER_REPO" rev-parse HEAD)" = "$PRODUCER_SHA"
test -z "$(git -C "$PRODUCER_REPO" status --porcelain)"
cd "$PRODUCER_REPO/.apm/skills/professor-contact/tests"

# 本版必须先验证：17项隔离判定正反例，及8项配置／身份记录自检。
uv run --offline --cache-dir /tmp/pc67-gate2-uv-cache python -m unittest -v \
  test_issue32_e2e_verifier.Issue67Stage4IsolationHarnessTests
uv run --offline --cache-dir /tmp/pc67-gate2-uv-cache python -m unittest -v \
  test_issue67_runtime_config.Issue67RuntimeConfigTests \
  test_issue67_runtime_evidence.Issue67RuntimeEvidenceTests
```

这些样例直接构造合法成功、违反冻结隔离要求的有效结果，以及缺失／矛盾归属、配置不符、旧临时会话等无效或不可观察证据；预期分别为 `PASS_TARGET`、`FAIL_PRODUCT`、对应的 `INVALID_TEST_EXECUTION`／`BLOCKED_OBSERVABILITY`。新增两个隔离样例只改变请求会话前提；旧业务正反例保留。记录器另拒绝恢复旧会话及缺少新版协议配置。样例是测试工程师规则第3.2.2节验证，不替代正式产品验收。

第25版准备脚本两项自检未修改，可复用其已保存的通过日志；本版8项受影响自检不能复用旧9项的总通过数。当前修改未执行上述命令，第二关口仍未完成。

未受影响证明保留原命令与通过来源，以下命令供定位，不要求本轮重复执行：
```bash
# PC67-DSTATE：16项
uv run --offline --cache-dir /tmp/pc67-gate2-uv-cache python -m unittest -v \
  test_contact_state.Issue67ProfessorLocalStage4Tests \
  test_issue67_gate2_r3.Issue67Gate2R3IdentityTests \
  test_contact_state.Issue67SameProfessorFailClosedTests
# PC67-DADJ：29项
uv run --offline --cache-dir /tmp/pc67-gate2-uv-cache python -m unittest -v \
  test_contact_state.Issue67AdjacentStateTests \
  test_stage3_stage4_caller_contract.Issue67AdjacentCallerContractTests \
  test_stage4_selection_agent_contract.Issue67Stage4SelectionContractTests \
  test_issue67_gate2_r3.Issue67Gate2R3SelectedRefreshTests \
  test_issue67_gate2_r3.Issue67Gate2R3SelectionContractTests
# PC67-WIRING：1项
uv run --offline --cache-dir /tmp/pc67-gate2-uv-cache python -m unittest -v \
  test_issue53_stage4_runtime_assets.Issue53Stage4RuntimeAssetTests.test_request_builder_emits_only_the_pc53_command_surface
# 第五阶段本地邮件包交接：1项
uv run --offline --cache-dir /tmp/pc67-gate2-uv-cache python -m unittest -v \
  test_stage5_dualtarget_contract.Stage5DualTargetContractTests.test_finalize_command_example_passes_the_professor_local_email_pack
```


## 3. `PC67-RISO` 当前唯一正式执行步骤

### 3.1 证明范围

负责证明：

- 输入合法的教授A，其第四阶段本地文件对可独立提交；
- 数据损坏的教授B不阻断A；B本地文件对零写入且故障字节保持；
- 项目级第四阶段文件对不恢复为正式数据来源，字节保持；
- 子线程可由适配器的正式关系归属；
- 规范化的 `professor_dir` 目录是身份依据。

不证明第五阶段业务正确性；提供方和模型可用性不是产品要求。

### 3.2 安装与独占目录

```bash
set -euo pipefail
umask 077
: "${FIXTURES:?set exact skills-test-fixtures checkout absolute path}"
: "${HARNESS_WORKSPACE:?set configured eval workspace absolute path}"

: "${PRODUCER_SHA:?set full commit from the canonical r26 publication}"
FIXTURE_SHA=c738fa2f8bcbb16cd99d741332d5f59b062b6357
MODEL=gpt-6-luna
REASONING=low

test "$(git -C "$FIXTURES" rev-parse HEAD)" = "$FIXTURE_SHA"
test -z "$(git -C "$FIXTURES" status --porcelain)"
jq -e '.contract_id == "skills-test-fixtures/codex-eval-adapter@16"' \
  "$FIXTURES/configs/codex-eval-adapter-contract.json"

TMP_BASE="${TMPDIR:-/tmp}"
CASE_ROOT="$(mktemp -d "${TMP_BASE%/}/pc67-r26.XXXXXX")"
CONSUMER_ROOT="$CASE_ROOT/consumer"
PROGRAM_ROOT="$CASE_ROOT/program"
PROFILE_ROOT="$CASE_ROOT/profile"
OUTPUT_DIR="$CASE_ROOT/evidence"
mkdir -p "$CONSUMER_ROOT" "$OUTPUT_DIR"
jq -n --arg producer_sha "$PRODUCER_SHA" --arg fixture_sha "$FIXTURE_SHA" \
  --arg consumer "$CONSUMER_ROOT" --arg program "$PROGRAM_ROOT" --arg profile "$PROFILE_ROOT" \
  --arg run_id "${CASE_ROOT##*/}" \
  '{producer_sha:$producer_sha,test_plan_revision:"issue-67-gate2-r26-2026-10-04",
    fixture_sha:$fixture_sha,fixture_worktree_clean:true,manual_patch:"no",
    fixture_run_id:$run_id,fixture_type:"stage4-isolation",
    consumer_root:$consumer,program_root:$program,profile_root:$profile}' \
  > "$OUTPUT_DIR/run-identity.json"

cd "$CONSUMER_ROOT"
apm install "https://github.com/ScholarWorkflow/professor-contact.git#$PRODUCER_SHA" \
  --target codex --trust-transitive-mcp > "$OUTPUT_DIR/install.log" 2>&1

SKILL_ROOT="$CONSUMER_ROOT/.agents/skills/professor-contact"
RUNTIME="$SKILL_ROOT/tests/runtime"
VERIFY_BASE="$RUNTIME/verify_issue32_e2e.py"
VERIFY_RISO="$RUNTIME/verify_issue67_riso.py"
BUILD_REQUEST="$RUNTIME/build_issue67_eval_request.py"
PREP_CASE="$RUNTIME/prepare_issue67_riso_case.py"
RECORD_RUNTIME="$RUNTIME/record_issue67_runtime_evidence.py"

for f in "$VERIFY_RISO" "$BUILD_REQUEST" "$PREP_CASE" "$RECORD_RUNTIME"; do test -f "$f"; done

uv run --offline --cache-dir /tmp/pc67-gate2-uv-cache python "$VERIFY_BASE" install \
  --consumer-root "$CONSUMER_ROOT" \
  --producer-sha "$PRODUCER_SHA" \
  --output "$OUTPUT_DIR/install-verdict.json"
jq -e '.status == "pass" and (.checks|length>0) and all(.checks[]; .status == "pass")' \
  "$OUTPUT_DIR/install-verdict.json"
```

安装只能来自生产仓库远端的完整提交；禁止本地路径、符号链接、可编辑安装、复制生成物或在消费者中手工打补丁。

### 3.3 用例准备与执行前快照

```bash
SOURCE_MANIFEST="$OUTPUT_DIR/source-fixture-manifest.json"
MANIFEST="$OUTPUT_DIR/fixture-manifest.json"

uv run --offline --cache-dir /tmp/pc67-gate2-uv-cache python "$PREP_CASE" \
  --program-root "$PROGRAM_ROOT" \
  --profile-root "$PROFILE_ROOT" \
  --source-output "$SOURCE_MANIFEST" \
  --output "$MANIFEST"

jq -e '
  .fixture_kind == "stage4-isolation"
  and .manual_patch == "no"
  and .case_preparer == "tests/runtime/prepare_issue67_riso_case.py"
  and .derivation.removed_valid_legacy_selection_rows == 1
' "$MANIFEST"

uv run --offline --cache-dir /tmp/pc67-gate2-uv-cache python "$VERIFY_BASE" stage4-snapshot \
  --program-root "$PROGRAM_ROOT" \
  --fixture-manifest "$MANIFEST" \
  --output "$OUTPUT_DIR/pre-snapshot.json"
jq -e '.status == "pass" and .isolation_pre != null' "$OUTPUT_DIR/pre-snapshot.json"
```

全部发生在 `CASE_STARTED` 前。准备程序只移除合法目标的一条旧选择行，使其迁移为 `not_applicable`；旧邮件包、损坏的B数据、项目级历史的其它字节和教授本地输入保持。

### 3.4 固定提示词、请求与输入摘要

```bash
PROMPT_SOURCE="$RUNTIME/prompts/issue67-stage4-isolation.txt"
PROMPT="$OUTPUT_DIR/issue67-stage4-isolation.txt"
REQUEST="$OUTPUT_DIR/eval-request.json"

uv run --offline --cache-dir /tmp/pc67-gate2-uv-cache python - "$PROMPT_SOURCE" "$PROMPT" "$PROGRAM_ROOT" <<'PY'
from pathlib import Path
import sys
src = Path(sys.argv[1]); out = Path(sys.argv[2]); root = Path(sys.argv[3]).resolve()
text = src.read_text(encoding="utf-8")
if text.count("<PROGRAM_ROOT>") != 1:
    raise SystemExit("prompt must contain exactly one <PROGRAM_ROOT>")
out.write_text(text.replace("<PROGRAM_ROOT>", str(root)), encoding="utf-8")
PY

uv run --offline --cache-dir /tmp/pc67-gate2-uv-cache python "$BUILD_REQUEST" \
  --consumer-root "$CONSUMER_ROOT" \
  --prompt-file "$PROMPT" \
  --model "$MODEL" \
  --reasoning "$REASONING" \
  --timeout 900 \
  --output "$REQUEST"

shasum -a 256 \
  "$MANIFEST" "$OUTPUT_DIR/pre-snapshot.json" "$PROMPT" "$REQUEST" \
  > "$OUTPUT_DIR/input-sha256.txt"

```

`CASE_STARTED` 紧接唯一 `/eval` 之前；此前失败均为 `CASE_NOT_STARTED`。

### 3.5 唯一正式 `/eval`

```bash
EVAL_PORT="$(direnv exec "$HARNESS_WORKSPACE" printenv EVAL_PORT)"
test -n "$EVAL_PORT"
touch "$OUTPUT_DIR/case-started.txt"

set +e
curl -sS --max-time 930 \
  -o "$OUTPUT_DIR/eval-response.json" \
  -w '%{http_code}\n' \
  -H 'Content-Type: application/json' \
  --data-binary @"$REQUEST" \
  "http://127.0.0.1:$EVAL_PORT/eval" \
  > "$OUTPUT_DIR/eval-http-status.txt" \
  2> "$OUTPUT_DIR/eval-curl-error.txt"
CURL_RC=$?
set -e
printf '%s\n' "$CURL_RC" > "$OUTPUT_DIR/eval-curl-exit-code.txt"
HTTP_CODE="$(tr -d '\r\n' < "$OUTPUT_DIR/eval-http-status.txt")"

case "$HTTP_CODE" in
  2??) ;;
  *) jq -n --arg http "$HTTP_CODE" --argjson curl_rc "$CURL_RC" \
       '{status:"blocked",classification:"BLOCKED_RUNTIME_PROVIDER",http_status:$http,curl_exit_code:$curl_rc}' \
       > "$OUTPUT_DIR/transport-verdict.json"; exit 2 ;;
esac
if test "$CURL_RC" -ne 0; then
  jq -n --arg http "$HTTP_CODE" --argjson curl_rc "$CURL_RC" \
    '{status:"blocked",classification:"BLOCKED_RUNTIME_PROVIDER",http_status:$http,curl_exit_code:$curl_rc}' \
    > "$OUTPUT_DIR/transport-verdict.json"
  exit 2
fi

jq -e '
  (.version|type) == "string" and (.version|length) > 0
  and (.passed|type) == "boolean"
  and (.output.backend|type) == "string" and (.output.backend|length) > 0
  and (.output.runtime_generation|type) == "number"
  and (.output.exit_code|type) == "number"
  and (.output.termination_reason|type) == "string"
  and (.output.thread_id|type) == "string" and (.output.thread_id|length) > 0
  and (.output.app_server_events|type) == "array"
' "$OUTPUT_DIR/eval-response.json"
```

不得重复采样来寻找更好的结果；提供方、模型或传输不可用且没有新诊断信息时停止。

### 3.6 运行身份记录、适配器与产品判定

先写本次实际运行证据：

```bash
uv run --offline --cache-dir /tmp/pc67-gate2-uv-cache python "$RECORD_RUNTIME" \
  --eval-request "$REQUEST" \
  --eval-response "$OUTPUT_DIR/eval-response.json" \
  --expected-model "$MODEL" \
  --expected-reasoning "$REASONING" \
  --output "$OUTPUT_DIR/runtime-evidence.json"

jq -e '
  .status == "ok"
  and .invocation.model == "gpt-6-luna"
  and .invocation.reasoning == "low"
  and .invocation.sandbox == "workspace-write"
  and .invocation.multi_agent_v2_enabled == true
  and .invocation.session_mode == "default_persistent"
  and .invocation.ephemeral == false
  and (.runtime.codex_version|type) == "string" and (.runtime.codex_version|length) > 0
  and (.runtime.backend|type) == "string" and (.runtime.backend|length) > 0
  and (.runtime.runtime_generation|type) == "number"
' "$OUTPUT_DIR/runtime-evidence.json"
```

这里的 `invocation.*` 从本次实际提交请求的参数读取；`runtime.*` 从同次 `/eval` 响应读取。它们只检查运行来源和方案一致性，不把版本号变成产品通过条件。

然后：

```bash
set +e
uv run --offline --cache-dir /tmp/pc67-gate2-uv-cache python \
  "$FIXTURES/scripts/parse_codex_eval_evidence.py" \
  --contract "$FIXTURES/configs/codex-eval-adapter-contract.json" \
  --eval-response "$OUTPUT_DIR/eval-response.json" \
  --consumer-root "$CONSUMER_ROOT" \
  --output "$OUTPUT_DIR/adapter.json" \
  > "$OUTPUT_DIR/adapter.stdout.txt" \
  2> "$OUTPUT_DIR/adapter.stderr.txt"
ADAPTER_RC=$?
set -e
printf '%s\n' "$ADAPTER_RC" > "$OUTPUT_DIR/adapter-exit-code.txt"
test "$ADAPTER_RC" -eq 0
jq -e '.adapter_contract_id == "skills-test-fixtures/codex-eval-adapter@16"' \
  "$OUTPUT_DIR/adapter.json"

set +e
uv run --offline --cache-dir /tmp/pc67-gate2-uv-cache python "$VERIFY_RISO" \
  stage4-professor-isolation \
  --expected-model "$MODEL" \
  --expected-reasoning "$REASONING" \
  --program-root "$PROGRAM_ROOT" \
  --fixture-manifest "$MANIFEST" \
  --pre-snapshot "$OUTPUT_DIR/pre-snapshot.json" \
  --eval-request "$REQUEST" \
  --input-sha256 "$OUTPUT_DIR/input-sha256.txt" \
  --eval-response "$OUTPUT_DIR/eval-response.json" \
  --adapter-output "$OUTPUT_DIR/adapter.json" \
  --install-verdict "$OUTPUT_DIR/install-verdict.json" \
  --producer-sha "$PRODUCER_SHA" \
  --fixture-sha "$FIXTURE_SHA" \
  --output "$OUTPUT_DIR/pc67-riso-verdict.json"
VERIFIER_RC=$?
set -e
printf '%s\n' "$VERIFIER_RC" > "$OUTPUT_DIR/verifier-exit-code.txt"
```

正式产品判定读取 `pc67-riso-verdict.json`：

- `status=pass` + `classification=PASS_TARGET` → `PASS`
- `classification=FAIL_PRODUCT` → `FAIL`
- `BLOCKED_OBSERVABILITY` 或提供方／传输不可用 → `BLOCKED`
- `INVALID_TEST_EXECUTION` → `INVALID_TEST_EXECUTION`

`runtime-evidence.json` 只能证明运行身份和方案一致性，不能把产品判定改成通过。

## 4. 执行前审核及判定边界

- 可执行性：新版合同、上游固定方案及持久会话实测支持该入口。安装仍用远端完整提交；模型和推理仍来自项目共识。当前产品业务运行尚未验证，不能保证新版一定消除旧线程存储错误。
- 隔离：使用独占消费者、业务、用户资料和证据目录；新运行不恢复旧线程；固定干净夹具且无手工补丁。变量路径及端口来源沿用上述步骤，运行实际值保存在记录和请求中。
- 可观察性：使用第16版三者联合归属；结构化创建调用的发送线程及调用编号须与子代理活动匹配，具体接收线程须有同一父来源的成功子线程读取。缺失归属为不可观察，矛盾归属为无效，不能用代理文字或任务名称推导线程身份。正式隔离事实仍来自文件内容／字节及归属关系。
- 判定区分能力：第2节固定17项隔离样例和8项受影响资产自检**尚未执行**，当前为未完成。此前15项判定样例通过不能覆盖本次请求检查修改。
- 本轮已读材料未发现需放宽的产品要求；当前关键缺口是修改后判定程序的实际三类结果验证，尚不能给第二关口通过结论。

停止与唯一判定：

1. 安装、准备、固定输入或端口取得失败，未创建开始标记：`CASE_NOT_STARTED`，保留已完成产物、日志及原因。
2. 正式启动后传输／提供方不可用：`BLOCKED`，保留请求、传输退出码、HTTP状态、错误及已有响应；不要求未来步骤产物。
3. 身份记录失败、固定输入不符、适配器契约不符、证据矛盾或配置偏离：`INVALID_TEST_EXECUTION`，保留原始证据及失败出口，不改判产品失败。
4. 适配器正常解析但归属证据不足：由产品判定器输出 `BLOCKED_OBSERVABILITY`，映射为 `BLOCKED`。
5. 有效执行违反本用例负责的隔离要求：`FAIL_PRODUCT`，映射为 `FAIL`。
6. 有效执行满足本用例全部要求：`status=pass` 且 `classification=PASS_TARGET`，映射为 `PASS`。仅记录器成功、传输成功或前置检查通过均不能替代该判定。

适配器出口非零、缺失输出或契约不符时，停止并归为无效证据；不得忽略出口，只使用碰巧存在的旧输出。所有停止均保留此前材料。最终判定命令非零时仍保存其判定文件及退出码。没有证据支持上述终态时记材料不足、第三关口未完成，不猜测结果。

第3.6节已按该顺序检查适配器出口及契约。正式运行无自动重试：本版是输入改变后的新执行，旧受阻尝试全部保留；不得在输出不理想时重新采样。成功与失败均保留安装证明、准备源／派生清单、快照、提示词、请求、输入摘要、实际身份记录、响应、适配器输出、判定、出口及其摘要。

## 5. 逐证明复用与重新执行

| 证明／用例 | 决定与来源 | 影响分析 |
| --- | --- | --- |
| `PC67-DSTATE` | `REUSE_PRIOR_PASS`，`4b0a115`，16项 | 状态代码及这些样例未变 |
| `PC67-DADJ` | `REUSE_PRIOR_PASS`，同提交29项 | 相邻阶段及负责者文档未变 |
| `PC67-WIRING` | `REUSE_PRIOR_PASS`，同提交1项 | 第53号请求入口未变 |
| 第五阶段本地邮件包交接 | `REUSE_PRIOR_PASS`，同提交1项 | 交接合同及文档未变 |
| `PC67-RISO-ORACLE` | `EXECUTE_CURRENT`，当前17项 | 请求判定及样例改变，旧15项结果不能代替 |
| `PC67-RBIND` | `REUSE_PRIOR_PASS`，`71eed2040541d1f557c0c4d5bdff64b9bf1d4e0e` | 绑定路径及其请求判定未变；共享文件只改第67号隔离入口 |
| `PC57-R2` | `REUSE_PRIOR_PASS`，`938ab56149b4dc50bdcf77e86c8c4077b012f694` | 缺选择与零写入路径未变 |
| 准备脚本自检2项 | `REUSE_PRIOR_PASS`，`a17aeb9`、第25版9项自检中的2项 | 准备输入、派生规则和程序未变 |
| 配置／记录自检8项 | `EXECUTE_CURRENT` | 持久会话、新版协议和一致性检查改变 |
| `PC67-RISO` | 第二关口通过后 `EXECUTE_CURRENT` | 夹具、观察合同及会话输入改变；旧运行无成功创建及业务执行事实，不能仅重新判读得到通过 |

确定性通过来源：[执行记录](https://github.com/ScholarWorkflow/professor-contact/pull/71#issuecomment-5954650694)，更新2026-10-02 14:28:46 UTC，含修复前失败及修复后五块完整日志。绑定通过：[正式执行](https://github.com/ScholarWorkflow/professor-contact/pull/71#issuecomment-5936979046)，更新2026-10-01 17:37:28 UTC，及[汇总](https://github.com/ScholarWorkflow/professor-contact/pull/71#issuecomment-5937316801)，更新17:58:03 UTC。缺选择通过：[执行记录](https://github.com/ScholarWorkflow/professor-contact/pull/71#issuecomment-5930070786)，更新2026-10-01 11:06:50 UTC。复用继承正式历史结果，不改写为当前执行。

## 6. 完整性、待办与当前结论

- 第一关口：保留第3版 `PASS`；版本和有效性核查完整，未重开。
- 第二关口：`INCOMPLETE`（未完成）；限定修订材料检查部分完成。缺少修改后第2节三类判定验证的命令、结果及日志，不能发布 `PASS + COMPLETE`。
- 第三关口：`NOT_READY`（未就绪），部分完成；必需隔离用例没有本版有效通过。旧第25版保持原 `BLOCKED`，本版未执行。
- 合并：`NOT_READY`。
- 产品、冻结需求及执行计划必须修改项：无。测试方案修正已经落实，但验证未完成。
- 仍缺的历史材料：第24版两次开始前安装失败的完整原始记录及再次启动依据；不能补造或覆盖。该缺失不妨碍判断当前未就绪。
- 无无法消解的需求或计划来源冲突；旧方案不自动获得新观察合同的覆盖。

推进顺序：**测试工程师**先核对并验证第2节受影响判定程序，保存全部三类结果；通过后在本版固定提交上确认第二关口，不增加无关检查。随后**本地执行代理**按本版执行一次 `PC67-RISO`，保留全部尝试与实际版本，再交**测试工程师**审核第三关口。若判定样例失败，测试工程师修正测试程序；若实际运行未遵守方案，本地执行代理纠正执行；若业务结果违反已明确计划，本地执行代理修复产品。当前正式计划已足够明确，没有需要执行计划工程师补充或重开计划审核的事实。
