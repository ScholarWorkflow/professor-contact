# 第66号议题第十版完整执行手册

测试计划版本：`issue-66-test-plan-r22-stage3-write-validation-r10-2026-10-09`。本手册对应第73号拉取请求的唯一有效测试计划；第十版设计审核为 `PASS`、`COMPLETE`。第九版执行手册保留为历史记录，不用其已撤回的写入前快照要求阻断本版。

## 阶段与范围

- 当前工作是本地测试工程师的材料准备。第二关口新增范围尚未批准，第三关口当前来源尚未通过；本轮没有发送正式模型请求。
- 本轮处理固定写入命令的运行时取证采集和判定：保留实际命令身份、参数、退出码、标准输出、输出文件字节、最终消息、保存摘要、运行归属和先后关系；不以缺少保存前存在性、权限或同步快照单独判无效。
- 本轮在拉取请求提交 `dc09a97f2dd074487ad83e9aad6f9ec45b767b55` 上运行。运行器记录的工作树包含四个测试实现文件及运行器本身的待提交改动；测试条目数来自实际结构化报告，不沿用历史固定总数。预存 `.tmp_scripts/` 未用于本轮脚本或证据，也未改动。
- 计划正文和审核记录：[第十版测试计划](issue-66-test-plan.md)、[第十版设计审核](issue-66-test-plan-review-r10.md)。正式验收依据、要求到用例的完整对应、固定写入判据及后续责任按计划原文执行。

## 本地候选运行

从仓库根目录运行。运行器在 `/private/tmp` 下创建独占证据目录；不要把临时脚本或预检产物放入仓库。

```bash
TMPDIR=/private/tmp UV_CACHE_DIR=/private/tmp/issue66-uv-cache \
  bash test-plan/issue-66-run.sh local
```

本轮实际证据目录：`/private/tmp/issue66-gate2-candidate.uY0ouyXf`。运行器版本：`issue-66-local-candidate-runner-r23-stage3-write-validation-r10-2026-10-09`。执行源提交记录为 `dc09a97f2dd074487ad83e9aad6f9ec45b767b55`；实际计划标记与运行器标记记录在 `metadata.txt`。本地运行使用 `uv 0.12.22`、`Python 3.14.6`、`GNU Bash 5.3.15` 和 `jq 1.8.2`；依赖按 `uv run --no-project` 运行，没有安装项目依赖。未使用模型或评估服务。可选的 `shellcheck` 未安装；运行器仍完成其余步骤。

八套结构化报告均为 `PASS`、退出码 `0`、零失败、证据有效；共执行271项：

| 套件 | 实际条目数 | 结果 |
| --- | ---: | --- |
| `judge` | 142 | `PASS` |
| `execution_wiring` | 39 | `PASS` |
| `structured_result` | 14 | `PASS` |
| `credential` | 17 | `PASS` |
| `local_state` | 12 | `PASS` |
| `validation_handoff` | 25 | `PASS` |
| `agent_contract` | 11 | `PASS` |
| `write_validation` | 11 | `PASS` |

`judge-samples.jsonl` 有174条判定样例记录、138个不同测试编号；`samples.tsv` 有72条样例记录，含表头共73行。`metadata.txt` 将样例账本记为 `VALID_JUDGE_AND_DIRECT_ASSERTION_RECORDS`。条目数按报告动态记录，不冻结为历史数量。

运行器在 `candidate-combinations/` 中核验的四种计划组合，实际值均符合独立预期：

| 组合 | 实际结果 | 有效性 | 独立产品失败数 |
| --- | --- | --- | ---: |
| `test_valid_candidate_all_checks_pass` | `PASS` | `VALID` | 0 |
| `test_valid_candidate_with_independent_product_failure` | `FAIL` | `VALID` | 1 |
| `test_invalid_ledger_keeps_independent_product_failure` | `INVALID_TEST_EXECUTION` | `INVALID` | 1 |
| `test_invalid_material_cannot_attribute_product_failure` | `INVALID_TEST_EXECUTION` | `INVALID` | 0 |

结构化结果套件还保存四个边界样例：空套件和缺失计划套件均归为 `INVALID_TEST_EXECUTION/INVALID/0`；软件元数据差异伴随独立产品失败仍为 `FAIL/VALID/1`；软件来源版本与摘要不同但其他证据有效仍为 `PASS/VALID/0`。这些报告不替代上述四种计划组合。

`candidate-result.json` 的实际字段为 `overall=PASS`、`evidence_validity=VALID`、`local_product_failures=[]`、`gaps=[]`、`runner_execution=COMPLETE`、`exit_code=0`。这只表示本轮本地候选材料有效且通过，不代表第二关口或正式验收通过。

审核时可直接按 JSON 字段复核：

```bash
EVIDENCE_DIR=/private/tmp/issue66-gate2-candidate.uY0ouyXf
jq -s '[.[] | {suite,result,actual_test_count,failures:(.failures|length),exit_code,evidence_validity}]' \
  "$EVIDENCE_DIR/suites.jsonl"
jq '{overall,evidence_validity,local_product_failures,gaps,runner_execution,exit_code}' \
  "$EVIDENCE_DIR/candidate-result.json"
jq -s 'length' "$EVIDENCE_DIR/judge-samples.jsonl"
```

证据目录保留 `metadata.txt`、逐命令记录、八份 `suite-*.json`、`suites.jsonl`、`samples.tsv`、`judge-samples.jsonl`、组合样例的输入/独立预期/实际结果/引用、`candidate-summary-input.json`、`candidate-result.json` 和 `outcome.txt`。完整证据留在 `/private/tmp`，不提交到仓库。

## 已有预检的复用边界

可复用的固定写入安装预检位于 `/private/tmp/issue66-r9-install-retry-original.u4YGZR6y/installation-check`。`install.json` 记录受支持的远端 APM 安装成功，来源提交为 `1a7040b2640043d26dfe62dc08b10f09df173ffe`，消费者新建且 `manual_patch=no`。`writer.json` 记录已安装 `stage3-write-validation` 的受控调用退出码为 `0`、调用前目标不存在、调用后存在、文件模式为 `0600`，并且标准输出与文件原始字节相同；`preflight.json` 和 `verdict.json` 均为 `PREFLIGHT_ONLY`，正式请求未尝试、未发送，`save_input=null`。

该预检只证明安装后的固定命令调用及其取证通道仍适用，不证明真实委派、业务结果或正式保存链。本地已安装脚本 `contact_state.py` 与当前工作树脚本的 `shasum -a 256` 均为 `312f0e81bd0c86b576d723782f41d31469436f5bf19680d72512e12ce5ce2869`，所以安装预检中的产品脚本行为可复用；若以后该脚本或相关运行前提变化，只重做受影响的受控检查。

原生事件字段形状复用第11次正式尝试 `/private/tmp/issue66-formal-pr73-fba6b1e-20261007-11/response-raw.json`。其原始响应含 `app_server_events`、`item/started`、`item/completed` 及 `commandExecution` 类型；对应 `verdict.json` 为 `INVALID_TEST_EXECUTION`，并记录原请求已尝试且已发送。它只用于核对事件结构，不作为产品通过或失败证据，也不能替代本轮未来正式请求的归属、输出和消费字节证据。

## 第二关口与正式执行前置

正式用例只有 `S3-RT-CODEX-1`。完成第二关口前不得调用正式模式。审核材料至少须包含：当前完整测试计划及审核记录、与计划一致的执行手册、测试和采集/判定实现、当前运行器、完整本地候选证据、上述受控安装预检复用依据、原生事件形状依据，以及对本轮修改范围和复用范围的审核。独立测试审核者须对第二关口全部材料作完整审核并明确批准；本地候选 `PASS` 不代替该批准。

获批后，正式执行者按批准来源和现有配置新建唯一正式证据目录，只执行一次正式请求。复用仍有效的成功安装和经核验的准备证据；正式命令使用现有 `test-plan/issue-66-formal.sh` 入口及其 `formal` 模式，不得启动、停止或检查评估服务，不得绕过项目入口、自动重试或因结果不理想再次请求。下面仅为获批后的命令模板，本轮未执行；须先填入批准的远端来源、既有消费者、安装记录和准备证据路径：

```bash
FORMAL_DIR="$(mktemp -d /private/tmp/issue66-r10-formal.XXXXXXXX)"
TMPDIR=/private/tmp UV_CACHE_DIR=/private/tmp/issue66-uv-cache \
  bash test-plan/issue-66-formal.sh formal \
    --repository "$PWD" \
    --fixture-root '<夹具仓库路径>' \
    --evidence-dir "$FORMAL_DIR" \
    --product-source '<第二关口批准的远端来源选择器>' \
    --consumer '<经核验的安装消费者目录>' \
    --installation-evidence '<成功安装记录 install.json>' \
    --preparation-evidence '<有效准备证据目录>'
```

正式证据须把同一运行和轮次中的固定命令身份、完整参数、退出码、标准输出、准备路径、输出文件实际字节、最终业务消息及保存完成事件的 `validation_sha256` 关联起来；保留教授、路径、调用归属和事件顺序。确定性测试及受控安装调用承担排他创建、模式 `0600`、同一文件描述符回读和故障清理证明。**不要求正式运行另行提供写入前存在性、非符号链接、保存前权限或同步文件快照**；缺少这些额外观察不能单独构成证据无效或第二关口阻断。若实际事件显示绕过固定命令、改写输出、摘要不符、归属冲突或顺序错误，按被观察到的具体事实判定。

正式结果按冻结方案归入 `PASS`、`FAIL`、`BLOCKED`、`NOT_TESTED`/`CASE_NOT_STARTED` 或 `INVALID_TEST_EXECUTION`。退出码或服务响应本身不等于业务通过；正式执行后由独立审核者依据同一运行的完整原始材料判定第三关口。
