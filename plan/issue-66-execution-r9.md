# 第66号议题第九版完整执行手册

计划版本：`issue-66-test-plan-r21-stage3-write-validation-r9-2026-10-08`。

本手册配合 [测试计划](issue-66-test-plan.md) 使用。独立只读审核记录 [r9 设计审核](issue-66-test-plan-review-r9.md) 已认定测试设计通过且审核完整；这只确认设计，不等于第二关口材料已通过。

## 当前事实与执行边界

- 本次只处理 `S3-WRITER-1`、`S3-ASSET-COMPAT-1`、`S3-HANDOFF-1`、`S3-RT-CODEX-1` 及其直接依赖。其他既有证明按计划复用，不重跑整套模型业务。
- 第二关口的新增材料仍须独立审核和批准；第三关口当前来源没有通过记录。本轮不运行正式模型请求。
- 先前三种 APM 网络路径均未完成安装：HTTPS 因依赖 `ScholarWorkflow/browser-pdf-tools` 的 TLS `unexpected eof while reading` 克隆失败并回滚；SSH 连接 22 端口被关闭；授权 HTTPS 重试在 `resolving` 停留 749.8 秒后中断。执行摘要记有该次中断的退出码 `130`，但旧目录 `/private/tmp/issue66-r9-preflight.9pzP6P` 没有单独保存每次顶层命令、分流标准输出与标准错误及进程退出码。该目录的顶层记录文件为 `candidate.md`、`install.log`、`install-ssh.log`、`install-escalated-retry.log`；失败安装还留下 `.agents/` 与 `.codex/` 部分文件树，日志记录了安装失败及删除 `apm.yml`。这些残留不算成功安装或可验证的独占消费者，旧尝试仍保留为记录不完整的预检事实。
- 先前用当时 PR 头 `5f5af167c4fe2a0f596dd978f8616d566e8b0ff7` 完成一次真实安装及受控 writer 预检。独占证据目录为 `/private/tmp/issue66-r9-install-final-20261008a`；其中 `install.json` 记载新消费者、远端来源及 APM 安装成功，`commands/013-install.json` 记录 `apm install --target codex --parallel-downloads 1 'ScholarWorkflow/professor-contact#5f5af167c4fe2a0f596dd978f8616d566e8b0ff7'` 和退出码 `0`。`writer.json` 记载已安装脚本的合成调用成功：退出码 `0`、目标调用前不存在、调用后存在、权限 `0600`，标准输出与文件原始字节相同。`preflight.json` 和 `verdict.json` 均标为 `PREFLIGHT_ONLY`，没有正式请求或 `save_input`；这只证明该提交的受控安装 writer 通道可用。
- 最终本地候选运行证据目录为 `/private/tmp/issue66-gate2-candidate.z5L3LLJJ`，产品来源为 `1a7040b2640043d26dfe62dc08b10f09df173ffe`，并使用本工作树中的最终测试运行器和测试文件。八套测试共 260 项全部通过；`candidate-result.json` 为 `PASS`、`VALID`、`COMPLETE`，运行器退出码为 `0`，没有候选级缺口或本地产品失败。该结论不表示第二关口已获批准，也不表示正式业务通过。
- 来源 `1a7040b2640043d26dfe62dc08b10f09df173ffe` 的隔离安装证据目录为 `/private/tmp/issue66-r9-install-pr73-1a7040b-20261008-candidate2`。安装器因 HTTPS 克隆传递依赖 `ScholarWorkflow/pdf-processing-core` 遇 TLS `unexpected eof while reading` 失败；`install.json` 的 `status` 为 `error`，`commands/013-install.json` 的退出码为 `1`。`writer.json` 与 `verdict.json` 均为 `CASE_NOT_STARTED`：未运行受控 writer，没有 `save_input`，也未发正式请求。`5f5af167c4fe2a0f596dd978f8616d566e8b0ff7` 的先前成功预检不能代替该来源的安装证据。
- 原始事件字段复核使用正式第 11 次尝试 `issue66-formal-pr73-fba6b1e-20261007-11` 的未改写 `response-raw.json`。该轮结论仍为 `INVALID_TEST_EXECUTION`，不能作业务通过或失败证据；这里只复用其原始事件形状。文件记录 `codex-cli 0.159.0-alpha.12.1` 和 2097 个原生事件，其中 `commandExecution` 各有 36 个 `item/started` 与 `item/completed`。两类事件均带 `message.params.threadId`、`turnId` 和 `item`；事件时间字段分别为 `startedAtMs` 与 `completedAtMs`。完成项中的 `item` 实际含 `id`、`type`、`command`、`cwd`、`status`、`exitCode`、`aggregatedOutput`；`aggregatedOutput` 有字符串和 `null` 两种值。该轮 12 个 Stage 3 完成命令中，11 个以零退出码完成、1 个以非零退出码结束；两条保存调用中，一条成功返回 JSON `status="ok"` 与 `validation_sha256`，一条返回错误。以上只说明本机已观察到的字段和保存返回形状，版本号只作来源记录，不构成版本门槛。
- 当时 `5f5af167c4fe2a0f596dd978f8616d566e8b0ff7` 的成功安装日志同时保留若干 APM 提示：`chrome-devtools` MCP 配置存在未知键、一个文件包含隐藏字符、OpenCode 目标包未安装、7 项依赖未固定、传递 MCP 需另行声明。该次 APM 安装命令返回 `0`，结构化安装状态为 `ok`；这些记录只属于当时的来源。
- 本轮补强了 writer 结果和原生调用取证：结果对象需通过完整字段、类型及计数关系校验；参数 JSON 与标准输出按精确 JSON 类型比较；非字符串或无法解析的工作目录、空或缺失教授身份、布尔类型退出码都不能成为成功证据。`cwd` 含空字符时的拒绝行为另经只读探针确认。相应接线与判定器测试已纳入上述 260 项候选运行。
- 任一关口的判定都以实际记录和原始材料为准。候选运行器显示执行完成不表示证据有效，也不表示产品通过。先前三条失败路径的原始调用记录仍有缺项；`5f5af167c4fe2a0f596dd978f8616d566e8b0ff7` 的早先成功预检只适用于当时来源；当前 `1a7040b2640043d26dfe62dc08b10f09df173ffe` 的隔离安装失败记录为 `CASE_NOT_STARTED`，两者均不构成正式业务通过。

## 计划范围与证明责任

| 用例 | 必须取得的事实 |
| --- | --- |
| `S3-WRITER-1` | 合法完整结果（包括 `pass`、`pass_with_minor`、`fail` 结论）由已安装固定命令排他写入；标准输出、文件字节和后续输入相同；非法输入、映射、冲突及部分失败符合计划。 |
| `S3-ASSET-COMPAT-1` | 源技能、代理说明和安装投影保留固定写入、只读兼容、有限写权限及错误停止要求；静态检查不冒充真实安装或正式运行。 |
| `S3-HANDOFF-1` | 准备返回路径、轮次、校验结果、固定 writer 输出、保存输入与后续记录按计划关联；原始字节一致。 |
| `S3-RT-CODEX-1` | 正式原生轨迹中的 writer 命令、thread/turn/item 身份、轮次、退出码、标准输出、临时输出文件观察、最终消息和保存输入均来自同一真实运行；事件缺失或错配不得推断为产品行为。 |

确定性检查只能证明其实际测试的内部行为。构造的样例不能替代安装成功事实、原生事件关系或正式运行文件。

## 来源与准备

1. 在 `ScholarWorkflow/professor-contact` 仓库根目录确认工作目录、代码来源和当前计划标记。运行记录要保存产品来源、测试来源、实际提交、工作树状态、时间、工具版本、执行入口及证据编号。提交摘要、干净工作树或与计划来源相同都不是通过门槛。
2. 本地夹具仓库使用已核对来源 `c738fa2f8bcbb16cd99d741332d5f59b062b6357`；适配器契约为 `skills-test-fixtures/codex-eval-adapter@16`。运行前以结构化记录确认实际夹具位置、来源、契约和适配器版本，并保留实际输出。不得手工复制或修补安装产物。
3. 正式运行与安装预检均需在仓库和工作树之外使用新建的独占证据目录及消费者目录。消费者不能复用，也不能放在产品仓库内。产品来源必须是 APM 支持的远端版本或提交选择器；不得传本地路径。保存实际来源，不要求其与测试来源版本相等。
4. 使用已配置的评估服务和项目规定入口取得服务地址；不得启动、停止、重启服务，也不得读取服务内部配置、进程、数据库或日志。不得绕过规定入口直接请求模型服务。
5. 本地运行器会记录 `uv`、Bash、`jq` 等实际使用工具的版本。若证据中出现 YAML、TOML 或 XML，再确认并记录对应 `yq` 或 `xmllint` 版本及解析输出。Python 命令使用 `uv run --no-project`，不安装项目依赖。

## 第一步：运行本地确定性候选检查

在仓库根目录执行一次本地运行器。它只运行本地确定性检查，不调用评估服务或模型；证据目录由脚本在 `/private/tmp` 下新建，权限受 `umask 077` 限制。

```sh
TMPDIR=/private/tmp bash test-plan/issue-66-run.sh local
```

入口只接受参数 `local`。不要手动复用或覆盖任何既有运行目录。脚本输出唯一证据目录；后续检查和审核都使用该目录。候选运行器版本应为 `issue-66-local-candidate-runner-r22-stage3-write-validation-r9-2026-10-08`，计划标记应为本手册开头的完整计划版本。

本地运行固定包含以下八个套件身份；**固定的是套件身份，实际测试条目数由每份结构化报告记录，不设固定总数**。

| 身份 | 测试程序 | 责任归属 |
| --- | --- | --- |
| `judge` | `test_issue66_runtime_judge.py` | `test_program` |
| `execution_wiring` | `test_issue66_execution_wiring.py` | `test_program` |
| `structured_result` | `test_issue66_suite_result.py` | `test_program` |
| `credential` | `test_issue66_invocation_credential.py` | `product` |
| `local_state` | `test_issue66_stage3_local_state.py` | `product` |
| `validation_handoff` | `test_issue66_validation_handoff.py` | `product` |
| `agent_contract` | `test_stage3_idea_generator_agent_contract.py` | `product` |
| `write_validation` | `test_issue66_stage3_write_validation.py` | `product` |

运行器对每个套件保存独立的 JSON 结果及状态来源、事件来源、实际测试数、条目编号和失败条目。套件身份必须各出现一次，每个套件至少有一个有效条目，实际条目数必须等于条目数组长度；条目编号和测试身份须唯一。前三个报告程序套件归 `test_program`，其报告自身失败属于无效测试执行，不能归因产品。其余套件归 `product`。

### 样例账本

检查 `samples.tsv` 和 `judge-samples.jsonl`。每条计划样例都要保留唯一编号、独立预期、实际观察、所属样例族、对应测试方法与调用序号、判定程序摘要、事件或直接断言、源代码位置及原始证据引用。运行器须以真实结构化测试事件映射判定样例；不得仅因日志里出现结论文字就填入实际结果。保留既有历史样例编号，不改写历史运行。

本次写入路径至少保留以下七类判定样例及其唯一来源：

| 样例编号 | 预期分类 | 所证明情形 |
| --- | --- | --- |
| `R21-9-E9` | `PASS` | 同一授权路径的 `fileChange Add` 是固定 writer 输出的重复视图，不应算第二次写入。 |
| `R21-9-E10` | `FAIL` | 未授权的其他路径仍构成产品写入范围违规。 |
| `R21-9-F18` | `BLOCKED` | 有效机器故障前缀在业务完成前阻断。 |
| `R21-9-F19` | `FAIL` | 固定写入非零退出后，校验者只报告结构化错误并在保存前正确停止。 |
| `R21-9-F20` | `FAIL` | 固定写入报错后根调用者继续保存，违反停止边界。 |
| `R21-9-F21` | `FAIL` | 固定写入报错后校验者仍报告业务成功，违反停止边界。 |
| `R21-9-I13` | `INVALID_TEST_EXECUTION` | 重复 writer 观察使证据无效，不能计为第二次产品写入。 |

样例实际结果必须与独立预期逐条对照。测试条目数、样例条目数或历史账本长度都不得被写成固定通过门槛。

### 候选汇总四种组合

检查 `candidate-combinations/` 下每种组合的 `raw-suite.json`、`input.json`、`independent-expected.json`、`actual.json`、`references.json`。预期必须独立于汇总程序输入；实际字段和原始引用须能相互定位。

| 组合 | 独立预期 | 用途 |
| --- | --- | --- |
| `test_valid_candidate_all_checks_pass` | `PASS`、证据 `VALID`、产品失败数为 0 | 有效候选全部通过。 |
| `test_valid_candidate_with_independent_product_failure` | `FAIL`、证据 `VALID`、产品失败数为 1 | 有效材料证明一项产品违约。 |
| `test_invalid_ledger_keeps_independent_product_failure` | `INVALID_TEST_EXECUTION`、证据 `INVALID`、仍保留 1 项独立产品失败 | 无效材料不抹掉能独立成立的产品失败。 |
| `test_invalid_material_cannot_attribute_product_failure` | `INVALID_TEST_EXECUTION`、证据 `INVALID`、产品失败数为 0 | 证据无效且失败不能独立归因产品。 |

汇总入口为 `.apm/skills/professor-contact/tests/runtime/issue66_candidate_classify.jq`。`runner_execution=COMPLETE` 只说明步骤已跑完，不替代 `overall`、证据有效性或关口审核。候选摘要的完整计划套件身份清单是八个；每套件的实际条目数仍动态记录。

## 第二步：检查本地证据结构

先保留运行器产生的原始文件，再解析结构化字段。JSON 和 JSONL 用 `jq`，YAML 或 TOML 用 `yq`，XML 用 `xmllint`；当前运行器的主要报告为 JSON、JSONL 和 TSV，未产生 YAML、TOML 或 XML 时，不要虚构对应证据。

```sh
EVIDENCE_DIR='<运行器打印的完整证据目录>'

jq -e '
  .schema == "issue66-candidate-result-v1"
  and (.overall == "PASS" or .overall == "FAIL" or .overall == "INVALID_TEST_EXECUTION")
  and (.runner_execution == "COMPLETE")
' "$EVIDENCE_DIR/candidate-result.json"

jq -e -s '
  length == 8
  and ([.[].suite] | sort) == ([
    "judge", "execution_wiring", "structured_result", "credential",
    "local_state", "validation_handoff", "agent_contract", "write_validation"
  ] | sort)
  and all(.[]; .actual_test_count > 0
    and .actual_test_count == (.items | length)
    and (.structured_status_source | type == "string" and length > 0)
    and (.raw_event_source | type == "string" and length > 0))
' "$EVIDENCE_DIR/suites.jsonl"

jq -e '
  .schema == "issue66-suite-result-v1"
  and .tests_run == (.tests | length)
  and .tests_run > 0
  and ([.tests[].ordinal] | length == (unique | length))
  and ([.tests[].test_id] | length == (unique | length))
' "$EVIDENCE_DIR/suite-write_validation.json"

jq -e -s 'length > 0 and all(.[]; type == "object"
  and (.sample_id | type == "string" and length > 0)
  and (.evidence_ref | type == "object"))' \
  "$EVIDENCE_DIR/judge-samples.jsonl"
```

上述检查中的 `8` 是固定套件身份数量，不是固定测试条目数量。TSV 列数、每行字段和账本映射由运行器自己的结构检查判定；同时查看 `commands/sample-ledger-assertion-diagnostics.*`、`commands/judge-ledger-validate.*` 及 `metadata.txt` 中账本状态。不能用文本搜索代替字段解析。

如果发现 YAML、TOML 或 XML 原始材料，另外按其真实格式解析，例如 `yq -e '.' file.yaml`、`yq -p=toml -e '.' file.toml`、`xmllint --noout file.xml`；只有材料确实存在且解析成功才记录通过。

## 第三步：真实安装及受控 writer 预检

需要补做预检且能取得远端产品来源时，使用新的外置唯一目录及新消费者。下方是命令模板；本节末尾记录的是当时 PR 头 `5f5af167c4fe2a0f596dd978f8616d566e8b0ff7` 的先前成功预检，不能代替来源 `1a7040b2640043d26dfe62dc08b10f09df173ffe` 的隔离安装证据。该来源的安装失败记录见本手册开头。旧失败事实必须原样保留，不得覆盖或重命名为成功。

```sh
REPO="$(pwd -P)"
FIXTURE_ROOT=/Users/rekidunois/code/skill-repos-dev/skills-test-fixtures
INSTALL_ROOT="$(mktemp -d /private/tmp/issue66-r9-install.XXXXXXXX)"

uv run --no-project python -B \
  .apm/skills/professor-contact/tests/runtime/issue66_execution.py \
  installation-check \
  --repository "$REPO" \
  --fixture-root "$FIXTURE_ROOT" \
  --evidence-dir "$INSTALL_ROOT/installation-check" \
  --product-source '<APM支持的远端版本或提交选择器>'
```

`--product-source` 仅填远端 ref 或提交选择器，不填本地路径，也不重复填写仓库名；程序将其绑定到 `ScholarWorkflow/professor-contact`。`--evidence-dir` 必须是尚不存在的新路径；程序在该证据目录下创建本次消费者和专用 `program`。不得传 `--consumer`、复用以往消费者、手工复制文件或修改安装投影。

该模式的顺序是：记录来源和工具 → 调用受支持的 APM 安装入口 → 只有安装成功后才调用安装消费者内的 `contact_state.py stage3-write-validation` → 保存实际命令、参数、退出码、标准输出原始字节、目标路径、文件字节、文件模式和调用前后存在性 → 写出预检结论。它不调用评估服务、不产生原生委派，也不证明正式业务流程。

若安装失败，运行器应保留安装调用记录和 `install.json`，把结果标为 `CASE_NOT_STARTED`，写明 `writer.json` 中没有受控调用且 `save_input` 为 `null`；立即停止，不构造正式业务输入、不探测或调用服务、不把失败归为产品违约。若安装成功但固定脚本缺失或证据不足，按记录判为 `BLOCKED` 或 `INVALID_TEST_EXECUTION`，不得补造文件事实。成功的合成 writer 调用只表示该受控检查完成；`preflight.json`/`verdict.json` 标记为 `PREFLIGHT_ONLY`，不能当作 `S3-RT-CODEX-1` 或第二关口通过。

先前成功预检所用的完整命令为：

```sh
TMPDIR=/private/tmp UV_CACHE_DIR=/private/tmp/issue66-uv-cache uv run --no-project python -B .apm/skills/professor-contact/tests/runtime/issue66_execution.py installation-check --repository /Users/rekidunois/.codex/worktrees/7bb3/professor-contact --fixture-root /Users/rekidunois/code/skill-repos-dev/skills-test-fixtures --evidence-dir /private/tmp/issue66-r9-install-final-20261008a --product-source 5f5af167c4fe2a0f596dd978f8616d566e8b0ff7
```

该先前命令的执行器退出码为 `0`。对照 `/private/tmp/issue66-r9-install-final-20261008a/install.json`、`writer.json`、`preflight.json`、`verdict.json` 和 `commands/` 中的逐命令标准输出、标准错误及退出码记录；这些证据只适用于当时 PR 头 `5f5af167c4fe2a0f596dd978f8616d566e8b0ff7`。来源 `1a7040b2640043d26dfe62dc08b10f09df173ffe` 的本次安装失败及 `CASE_NOT_STARTED` 记录见本手册开头，不能由先前成功预检替代。更早失败尝试的命令和输出缺口仍须如实保留。该合成 writer 检查不运行正式评测，不构成原生委派或第三关口证据。

## 第四步：第二关口材料独立审核

在交测试审核者前，准备同一版本的完整材料：权威计划全文、r9 设计审核、此手册、所有新增/修改的测试与运行器、完整本地候选证据目录，以及真实 APM 安装尝试的原始命令、标准输出、标准错误、退出码和结论。先前三次失败尝试没有执行器生成的 `CASE_NOT_STARTED` 结构化记录；该旧缺项须如实保留，不得把有日志误写成通过。当时 PR 头 `5f5af167c4fe2a0f596dd978f8616d566e8b0ff7` 的先前成功预检材料见 `/private/tmp/issue66-r9-install-final-20261008a`；当前来源 `1a7040b2640043d26dfe62dc08b10f09df173ffe` 的安装失败材料见 `/private/tmp/issue66-r9-install-pr73-1a7040b-20261008-candidate2`。两者各自对应的来源和结论不得混用。若后续预检没有完成，也须保留对应的未完成事实和缺失项。

审核者需覆盖四项计划范围、每项来源和执行入口、动态套件条目、样例账本、四种汇总组合、写入字节/权限观察与失败分流。只有独立审核确认第二关口全部材料可用并明确批准，才可进入正式执行。若审核发现问题，按责任归因修复后由新的独立审核者重新完整审核。

## 第五步：正式运行（本轮禁止执行）

**本轮不得调用以下正式模式**。仅在第二关口完整审核通过后，由正式执行者建立全新的正式证据目录，并以本轮实际远端产品来源调用一次。正式模式读取既有评估服务端口，通过项目评估入口只发送一次请求；不得启动服务、绕过入口、自动重试或因结果不理想再次调用。正式模式会新建独占消费者并重新执行安装，因此安装或环境失败应先保存事实并停止。

```sh
REPO="$(pwd -P)"
FIXTURE_ROOT=/Users/rekidunois/code/skill-repos-dev/skills-test-fixtures
FORMAL_ROOT="$(mktemp -d /private/tmp/issue66-r9-formal.XXXXXXXX)"

uv run --no-project python -B \
  .apm/skills/professor-contact/tests/runtime/issue66_execution.py \
  formal \
  --repository "$REPO" \
  --fixture-root "$FIXTURE_ROOT" \
  --evidence-dir "$FORMAL_ROOT/formal" \
  --product-source '<已由第二关口批准的远端版本或提交选择器>'
```

执行前再次确认该证据目录不存在、同一正式用例尚未发出请求、来源与批准记录一致。该程序把请求次数记录为 1 且最大次数为 1；一旦创建 `attempt.json` 或确认请求已尝试，就不得再次调用。零字节上传且无 HTTP 响应按 `CASE_NOT_STARTED` 保留；已尝试但传输未完成或无法确认按 `BLOCKED` 处理；不得重试。

原生收集须读取未改写的 `response-raw.json` 中 `output.app_server_events`。上段所列历史原始响应是 `item/started`、`item/completed` 和 `commandExecution` 字段的来源依据；完成状态、退出码及输出只能从同一完成事件读取。`writer.json` 使用 `issue66.writer-observation.v1`，并把实际 `commandExecution` 身份、命令参数、完成退出状态、标准输出字节、临时 handoff 输出的存在性/字节/模式、轮次、最终消息及 `save_input` 绑定同一 `evidence_set_id`。保存输入若取自请求完成后的文件观察，必须再由唯一原生保存完成事件的成功结构化返回值及 `validation_sha256` 绑定到同一字节；路径、轮次、摘要或调用身份任一不匹配时不得填入 `save_input`。这项摘要核对可证明保存命令消费了相同字节，但不能单独证明文件模式和观察时刻；材料必须另有保存前观察或经独立审核认可的可信等价依据，否则第二关口仍不完整。判定器通过 `--writer-evidence` 接收该材料。事件缺失时如实记缺口；不得用合成事件、`fileChange Add`、静态约定或单独的成功退出替代写入字节、模式、生产者和保存输入的证明。

## 输出目录和归档

本地候选运行目录至少包括：

- `metadata.txt`、`commands.tsv`、`suites.tsv`、`suites.jsonl`、`samples.tsv`、`judge-samples.jsonl`。
- `suite-<套件名>.json` 及 `commands/` 下逐条命令、原始标准输出、标准错误、退出码记录和报告校验结果。
- `candidate-combinations/<组合名>/` 下五份样例文件；根目录的 `candidate-summary-input.json`、`candidate-result.json`、`outcome.txt`。

安装预检目录记录 `versions.json`、`provenance.json`、`commands/`、`install.json`、`writer.json`、`verdict.json` 和 `preflight.json`。正式运行还应保留 `request.json`、`request-configuration.json`、`attempt.json`、`transport.json`、原始 `response-raw.json`、适配器原始与派生结果、前后快照、`routing.json`、`fixture.json`、`writer.json`、`judge-verdict.json` 及最终 `verdict.json`。只归档真实生成的文件，不补空文件伪装已观察。

所有输出路径留在仓库及工作树之外。保存完整原始文件、标准输出、标准错误、退出码、来源指针和唯一运行编号；不要清理失败证据，不覆盖旧目录，不把不同运行编号的输入或输出拼在一起。

## 分类、失败处理与结束条件

| 分类 | 何时使用 | 后续处理 |
| --- | --- | --- |
| `PASS` | 有效证据满足该项全部要求，且业务达到要求终态。 | 交独立关口审核；本地候选 `PASS` 本身不批准第二或第三关口。 |
| `FAIL` | 有效且可归因的材料证明产品违反明确要求。 | 保留事件、差异、路径和产品责任；不得用无效材料扩大归因。合法结果对象中的 `result: fail` 仍可成功写入。 |
| `BLOCKED` | 有效环境或故障证据显示业务未完成，但不能归因产品。 | 保留已证明事实，停止业务续行，不重试正式请求。 |
| `CASE_NOT_STARTED` / `NOT_TESTED` | 用例未进入被测边界或尚未执行；例如安装失败且 writer 未调用。 | 保留实际失败和未执行范围；不得记作产品 `FAIL`，也不得伪称通过。 |
| `INVALID_TEST_EXECUTION` | 输入、运行关联、事件顺序、解析、样例账本或判定材料无效。 | 保留全部原始材料并标出缺口；只保留能独立成立的局部产品失败。 |

本地运行器退出码：候选 `PASS` 为 0，`FAIL` 为 1，证据无效为 2；应同时读取 `candidate-result.json` 的结构化字段。单一命令失败、安装中断或材料缺失不能通过文本日志猜作产品失败。完成运行器全部步骤但账本无效，仍是无效证据。

第二关口独立审核通过后，正式执行者才可最多发出一次请求。第三关口审核者依据同一正式运行的完整原始材料作出结论；历史第七版通过、预检样例、合成 writer 调用或候选运行器通过，均不能替代第三关口当前来源结论。
