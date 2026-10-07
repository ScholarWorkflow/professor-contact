# 第 66 号测试安装与执行接线（R7）

本文件执行方式依照 `issue-66-test-plan-r19-clarification-r7-2026-10-07`，取代 R6 的固定提交、软件摘要、工具次版本、候选冻结及审批锁要求。产品、测试、判定程序、夹具、适配器、工具和运行配置均记录本次实际值，不与历史值比较。Gate 2 当前未通过；不得运行正式 `/eval`。

## 本地确定性候选

在仓库根目录运行七个确定性套件：

```sh
bash test-plan/issue-66-run.sh local
```

运行器不安装产品、不启动或连接评测服务、不发送 `/eval`。当前来源提交 `2723996424c6485fb61efcb4808a8e55c1d71cdd` 的候选已于 2026-10-07 完成；来源 `2497dae2fffc02b0a66d33ea33b0405e128a9154` 的有效失败保留为历史，见[测试计划](issue-66.md)。Gate 2 仍未通过，Gate 3 和正式 `/eval` 均未运行。实际来源和配置字段记录在各轮证据目录：产品及测试来源、仓库路径、提交与工作树状态、计划和判定程序来源、夹具及适配器来源、工作目录、`UV_CACHE_DIR`、`uv`、Python、Bash、`jq`、`rg`、`git`、`shasum` 及可用工具版本。确定性套件不使用产品安装、夹具、适配器或模型时，记明未使用；不填造正式运行值。

逐套件保存实际命令、结构化身份和条目、结果、原始标准输出与标准错误、退出码。证据目录还保存 `suites.tsv`、`suites.jsonl`、`samples.tsv`、`judge-samples.jsonl`、四类 `candidate-combinations`、`candidate-result.json`、运行元数据及编号。条目数和失败身份来自当次回调，不按历史数量或失败名称判定。账本逐条比较独立业务预期与实际结果；四种候选汇总组合仍须自洽。`runner_execution=COMPLETE` 只说明执行步骤结束。

本轮执行 `bash test-plan/issue-66-run.sh local`，证据目录基名为 `issue66-gate2-candidate.RGFhzJ3R`。`candidate-result.json` 记录 `evidence_validity=VALID`、`overall=PASS`、退出码 `0`、`runner_execution=COMPLETE`、`local_product_failures=[]`、`gaps=[]`；样例账本为 `VALID`，`sample_ledger_exit_code=0`，`combination_check_exit_code=0`。七套件全部通过，共 199 项：`judge` 114、`execution_wiring` 14、`structured_result` 11、`credential` 17、`local_state` 12、`validation_handoff` 22、`agent_contract` 9。交接目录修复回归通过；代理约定只记录本轮通过结果，不推断此前失败的具体修复原因。详见[当前候选结果](issue-66.md#r7-本地候选实际结果)。此前来源 `2497dae2fffc02b0a66d33ea33b0405e128a9154` 的证据目录基名为 `issue66-gate2-candidate.vno2ISAS`，结论为有效 `FAIL`、退出码 `1`，作为历史保留；不在此重复其临时目录绝对路径。软件版本或摘要即使记录，也只作来源定位。

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

2026-10-07 已运行正式 `preflight`。产品来源是 PR 提交 `2723996424c6485fb61efcb4808a8e55c1d71cdd` 的干净源码归档；证据集编号为 `issue66-r7-preflight-2723996424c6485fb61efcb4808a8e55c1d71cdd`。结果是 `CASE_NOT_STARTED`，`formal_request_sent=false`：产品和依赖安装命令退出 `1`，下载 `ScholarWorkflow/base-skills` 时 GitHub 连接在传输中断开，日志记录 `unexpected eof`。安装未完成，所以输入、请求及运行前快照也未准备；本轮预检未完成，不得记作通过。

首次尝试还发现预检模式不该读取 `EVAL_PORT`，现已改为先完成安装和预检准备，再仅在正式模式读取端口；新增接线回归覆盖此行为。后续重试使用单次依赖下载，但仍在同一依赖的 GitHub 下载处中断。没有发送正式请求，也没有运行 `/eval`。原始命令和输出保留在该证据集的 `commands` 目录。

## 正式配置负责服务隔离

R7 规定由正式评估配置负责建立独立运行目录。本地测试工程师使用既有评估服务，不启动、停止或重启服务，不读取服务进程、配置文件、数据库或日志，也不增加服务内部隔离检查。无需通过检查服务内部状态来复核正式配置。

执行器如准备独立预检，只能按已批准的本轮范围处理输入、初态、请求构造及运行前快照；不检查评估服务内部状态。预检不构成 Gate 2 批准。

## Gate 2 与正式 `/eval`

当前 Gate 2 未通过，Gate 3 未运行；不得运行正式 `/eval`。即使本地候选通过，也不会自动批准 Gate 2。

只有 Gate 2 审核者明确通过后，执行责任人才能另行决定正式运行。正式评测使用正式评估配置建立的独立运行目录；本地执行不检查评估服务内部状态。正式请求前须按获批步骤记录实际产品来源、模型和运行配置、安装输入、原始响应关联方式、请求前后业务文件状态、正式根与子线程关系及判定结果。正式调用最多一次，不自动重试；失败、阻断及无效证据均保留原始材料。

正式脚本通过相同入口接收必填 `--product-source`，不再要求 `--frozen-manifest` 或固定候选摘要。Gate 2 审核没有通过时，不执行以下模式：

```sh
UV_CACHE_DIR="$UV_CACHE_DIR" \
  bash test-plan/issue-66-formal.sh formal \
  --fixture-root "$FIXTURE_ROOT" \
  --evidence-dir "$NEW_EVIDENCE_DIRECTORY" \
  --product-source "$PRODUCT_SOURCE"
```

真实正式运行后的生产、保存、记录、权限、顺序、停止和终态事实，目前均未形成；不得用本地样例或历史探测替代。
