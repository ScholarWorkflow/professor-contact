# 第 66 号测试安装与执行接线（R7）

本文件执行方式依照 `issue-66-test-plan-r19-clarification-r7-2026-10-07`，取代 R6 的固定提交、软件摘要、工具次版本、候选冻结及审批锁要求。产品、测试、判定程序、夹具、适配器、工具和运行配置均记录本次实际值，不与历史值比较。Gate 2 当前未通过；不得运行正式 `/eval`。

## 本地确定性候选

在仓库根目录运行七个确定性套件：

```sh
bash test-plan/issue-66-run.sh local
```

运行器不安装产品、不启动或连接评测服务、不发送 `/eval`。2026-10-07 已在 PR 当前头提交 `bbe44511e0acf5ae1365eb4727ab34c1b892e33c` 上复验候选，结构化结果、套件计数及文件摘要见下文；前一轮基线 `2723996424c6485fb61efcb4808a8e55c1d71cdd` 的结果保留为历史。来源 `2497dae2fffc02b0a66d33ea33b0405e128a9154` 的有效失败也保留为历史，见[测试计划](issue-66.md)。Gate 2 仍未通过，Gate 3 和正式 `/eval` 均未运行。实际来源和配置字段记录在各轮证据目录：产品及测试来源、仓库路径、提交与工作树状态、计划和判定程序来源、夹具及适配器来源、工作目录、`UV_CACHE_DIR`、`uv`、Python、Bash、`jq`、`rg`、`git`、`shasum` 及可用工具版本。确定性套件不使用产品安装、夹具、适配器或模型时，记明未使用；不填造正式运行值。

逐套件保存实际命令、结构化身份和条目、结果、原始标准输出与标准错误、退出码。证据目录还保存 `suites.tsv`、`suites.jsonl`、`samples.tsv`、`judge-samples.jsonl`、四类 `candidate-combinations`、`candidate-result.json`、运行元数据及编号。条目数和失败身份来自当次回调，不按历史数量或失败名称判定。账本逐条比较独立业务预期与实际结果；四种候选汇总组合仍须自洽。`runner_execution=COMPLETE` 只说明执行步骤结束。

### PR 当前头提交复验（最新）

2026-10-07 在 PR 当前头提交 `bbe44511e0acf5ae1365eb4727ab34c1b892e33c` 执行 `bash test-plan/issue-66-run.sh local`，证据目录基名为 `issue66-gate2-candidate.Sw2XGr9j`。`candidate-result.json` 记录 `evidence_validity=VALID`、`overall=PASS`、退出码 `0`、`runner_execution=COMPLETE`、`local_product_failures=[]`、`gaps=[]`；样例账本为 `VALID`，`sample_ledger_exit_code=0`，`combination_check_exit_code=0`。七套件均为 `PASS` 且证据有效，共 199 项：`judge` 114、`execution_wiring` 14、`structured_result` 11、`credential` 17、`local_state` 12、`validation_handoff` 22、`agent_contract` 9。`candidate-result.json` 的 SHA-256 为 `91e23821c5567b4876d6f13cd77e3a8b6692c88818a5c2c85c0ddb50f723bb28`；`suites.jsonl` 的 SHA-256 为 `5369e3b7b2e04a29769532b9b2b9b20ad3d442285692b6f5a47ff5ce6318573b`。完整结果与逐套件有效性见[本地候选实际结果](issue-66.md#r7-本地候选实际结果)。Gate 2 未批准，Gate 3 与正式 `/eval` 未运行；候选通过不构成正式验收。

### 前一轮候选（历史）

此前执行 `bash test-plan/issue-66-run.sh local`，证据目录基名为 `issue66-gate2-candidate.RGFhzJ3R`。`candidate-result.json` 记录 `evidence_validity=VALID`、`overall=PASS`、退出码 `0`、`runner_execution=COMPLETE`、`local_product_failures=[]`、`gaps=[]`；样例账本为 `VALID`，`sample_ledger_exit_code=0`，`combination_check_exit_code=0`。七套件全部通过，共 199 项：`judge` 114、`execution_wiring` 14、`structured_result` 11、`credential` 17、`local_state` 12、`validation_handoff` 22、`agent_contract` 9。该证据记录的基线提交为 `2723996424c6485fb61efcb4808a8e55c1d71cdd`，并如实记录了当时的工作树修改；这些修改已提交并推送。交接目录修复回归通过；代理约定只记录该轮通过结果，不推断此前失败的具体修复原因。此前来源 `2497dae2fffc02b0a66d33ea33b0405e128a9154` 的证据目录基名为 `issue66-gate2-candidate.vno2ISAS`，结论为有效 `FAIL`、退出码 `1`，作为历史保留；不在此重复其临时目录绝对路径。软件版本或摘要即使记录，也只作来源定位。

## 安装和预检入口

正式包装器删除 Python 次版本限制，并把其余参数原样交给执行器。执行器要求本次产品来源 `--product-source`、夹具根目录和独占证据目录；包装器本身补充当前仓库路径。运行环境准备者提供本次实际的绝对路径和来源选择器：

```sh
UV_CACHE_DIR="$UV_CACHE_DIR" \
  bash test-plan/issue-66-formal.sh installation-check \
  --fixture-root "$FIXTURE_ROOT" \
  --evidence-dir "$NEW_EVIDENCE_DIRECTORY" \
  --product-source "$PRODUCT_SOURCE"
```

需要执行安装检查或 Gate 2 审核所需预检时，使用相同参数格式和本次实际来源：

```sh
UV_CACHE_DIR="$UV_CACHE_DIR" \
  bash test-plan/issue-66-formal.sh preflight \
  --fixture-root "$FIXTURE_ROOT" \
  --evidence-dir "$NEW_EVIDENCE_DIRECTORY" \
  --product-source "$PRODUCT_SOURCE"
```

每次使用从未存在的独占证据目录。记录实际产品来源选择器、实际测试和夹具来源、安装命令、工作目录、工具及模型配置、执行编号、每条命令及原始输出和退出码。来源、版本或未提交状态差异本身不拒绝执行；不得使用软件文件摘要或锁文件版本代替业务证据。

### 本轮 R7 预检结果

2026-10-07 最新正式 `preflight` 已成功完成。产品来源为 PR 提交 `0896243702c959da8e4981bffacfe820b06719b6` 的干净源码归档；证据集编号为 `issue66-r7-preflight-now-45b81f3`。`install.json` 记录安装入口检查通过、退出码 `0`，锁文件解析成功；安装器报告 318 秒内安装 10 个依赖。`preflight.json` 记录 `classification=PREFLIGHT_ONLY`、`formal_request_sent=false`，并确认安装、初始输入、请求构造和运行前快照都已准备。预检已完成；它不构成 Gate 2 批准，也没有发送正式请求或运行 `/eval`。

此前的失败尝试保留为历史：首次预检发现预检模式误读 `EVAL_PORT`，现已改为只有正式模式才读取端口，并增加接线回归；提交 `2723996424c6485fb61efcb4808a8e55c1d71cdd` 的尝试，以及提交 `45b81f3458dbeb5ed3ea5855823cc0cef19ed509` 的普通 HTTPS、HTTP/1.1 重试，均因 GitHub 依赖下载中断而未完成。最新成功结果保存在独立证据集中；各轮原始命令和输出保留在各自 `commands` 目录。

## 正式配置负责服务隔离

R7 规定由正式评估配置负责建立独立运行目录。本地测试工程师使用既有评估服务，不启动、停止或重启服务，不读取服务进程、配置文件、数据库或日志，也不增加服务内部隔离检查。无需通过检查服务内部状态来复核正式配置。

执行器如准备独立预检，只能按已批准的本轮范围处理输入、初态、请求构造及运行前快照；不检查评估服务内部状态。预检不构成 Gate 2 批准。

## Gate 2 与正式 `/eval`

当前 Gate 2 未通过，Gate 3 未运行；不得运行正式 `/eval`。即使本地候选通过，也不会自动批准 Gate 2。

只有 Gate 2 审核者明确通过后，执行责任人才能另行决定正式运行。正式评测使用正式评估配置建立的独立运行目录；本地执行不检查评估服务内部状态。正式请求前须按获批步骤记录实际产品来源、模型和运行配置、安装输入、原始响应关联方式、请求前后业务文件状态、正式根与子线程关系及判定结果。正式调用最多一次，不自动重试；失败、阻断及无效证据均保留原始材料。

### 正式请求传输失败判定与单次尝试

执行器只调用一次 `curl`，不重试。它在调用前独占写入 `attempt.json`，记录本轮请求摘要、请求体字节数和唯一尝试编号；调用后独占写入 `transport.json`，保留原始状态及上传计数输出、退出码、实际上传字节数和 HTTP 状态。两份记录均不覆盖。

`formal_request_attempted=true` 只表示执行器已尝试启动这一次请求；`formal_request_sent=true` 只表示客户端报告至少上传了一个请求体字节。两者都不表示服务端已接受请求。请求体传输是本接线判断是否到达被测启动边界的依据：只有确认客户端进程未启动，或没有 HTTP 响应且上传为零字节，才判 `CASE_NOT_STARTED`。收到非成功 HTTP 状态、请求体已上传但没有成功响应，或上传量及响应无法确认，均判 `BLOCKED`；不记作产品 `FAIL` 或 `INVALID_TEST_EXECUTION`。HTTP 状态为 200、上传完整且客户端退出码为零后，才继续解析正式业务证据；传输成功本身不代表业务通过。测试程序、样例、证据归属或记录损坏仍按 `INVALID_TEST_EXECUTION` 处理。

正式脚本通过相同入口接收必填 `--product-source`，不再要求 `--frozen-manifest` 或固定候选摘要。Gate 2 审核没有通过时，不执行以下模式：

```sh
UV_CACHE_DIR="$UV_CACHE_DIR" \
  bash test-plan/issue-66-formal.sh formal \
  --fixture-root "$FIXTURE_ROOT" \
  --evidence-dir "$NEW_EVIDENCE_DIRECTORY" \
  --product-source "$PRODUCT_SOURCE"
```

真实正式运行后的生产、保存、记录、权限、顺序、停止和终态事实，目前均未形成；不得用本地样例或历史探测替代。
