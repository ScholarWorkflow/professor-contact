# 第 66 号测试安装与执行接线（R7 历史记录；R20 待审候选）

本文件前半部分保留 `issue-66-test-plan-r19-clarification-r7-2026-10-07` 的历史执行方式和结果。当前唯一待审候选为 `issue-66-test-plan-r20-stage3-write-validation-r8-2026-10-08`，由末尾 R20 章节定义；正式执行器的 `PLAN` 标识必须与此候选完全一致。R7/R19 记录只作历史，不能给 R20 提供新命令的证据。Gate 2 当前 pending；不得运行正式 `/eval`。

## 本地确定性候选

在仓库根目录运行七个确定性套件：

```sh
bash test-plan/issue-66-run.sh local
```

运行器不安装产品、不启动或连接评测服务、不发送 `/eval`。2026-10-07 在提交 `240dc1236e514344bf61a340cbe1cf89943efd28` 完成最新候选，结构化结果、套件计数及文件摘要见下文；此前提交 `2d874c46f8a228ca390a17d2b9ff560db9b75578`、`bbe44511e0acf5ae1365eb4727ab34c1b892e33c` 与基线 `2723996424c6485fb61efcb4808a8e55c1d71cdd` 的结果保留为历史。来源 `2497dae2fffc02b0a66d33ea33b0405e128a9154` 的有效失败也保留为历史，见[测试计划](issue-66.md)。Gate 2 仍未通过，Gate 3 和正式 `/eval` 均未运行。实际来源和配置字段记录在各轮证据目录：产品及测试来源、仓库路径、提交与工作树状态、计划和判定程序来源、夹具及适配器来源、工作目录、`UV_CACHE_DIR`、`uv`、Python、Bash、`jq`、`rg`、`git`、`shasum` 及可用工具版本。确定性套件不使用产品安装、夹具、适配器或模型时，记明未使用；不填造正式运行值。

逐套件保存实际命令、结构化身份和条目、结果、原始标准输出与标准错误、退出码。证据目录还保存 `suites.tsv`、`suites.jsonl`、`samples.tsv`、`judge-samples.jsonl`、四类 `candidate-combinations`、`candidate-result.json`、运行元数据及编号。条目数和失败身份来自当次回调，不按历史数量或失败名称判定。账本逐条比较独立业务预期与实际结果；四种候选汇总组合仍须自洽。`runner_execution=COMPLETE` 只说明执行步骤结束。

### 最新本地候选

2026-10-07 在提交 `240dc1236e514344bf61a340cbe1cf89943efd28` 执行 `bash test-plan/issue-66-run.sh local`，证据目录基名为 `issue66-gate2-candidate.KdGywXke`。`candidate-result.json` 记录 `evidence_validity=VALID`、`overall=PASS`、`exit_code=0`、`runner_execution=COMPLETE`、`local_product_failures=[]`、`gaps=[]`；`candidate-summary-input.json` 中 `ledger.validity=VALID`、`sample_ledger_exit_code=0`、`combination_check_exit_code=0`。七套件均为 `PASS` 且证据有效，共 212 项：`judge` 114、`execution_wiring` 24、`structured_result` 14、`credential` 17、`local_state` 12、`validation_handoff` 22、`agent_contract` 9。`candidate-result.json` 的 SHA-256 为 `91e23821c5567b4876d6f13cd77e3a8b6692c88818a5c2c85c0ddb50f723bb28`；`suites.jsonl` 的 SHA-256 为 `871f754314bbb705f903e6b7c757665a5e0991349b3448469eb6b2ea9aa69a3f`。完整结果与逐套件有效性见[本地候选实际结果](issue-66.md#r7-本地候选实际结果)。Gate 2 未批准，Gate 3 与正式 `/eval` 未运行；候选通过不构成正式验收。

### 上一轮候选（历史）

2026-10-07 在提交 `2d874c46f8a228ca390a17d2b9ff560db9b75578` 执行同一命令，证据目录基名为 `issue66-gate2-candidate.spslDkEj`。七套件均通过且证据有效，共 207 项；样例账本与四种候选汇总组合均有效。该轮 `candidate-result.json` 摘要为 `91e23821c5567b4876d6f13cd77e3a8b6692c88818a5c2c85c0ddb50f723bb28`，`suites.jsonl` 摘要为 `bc317c11939b6462689bf3a98ac32caa56fb7a6a31b2563f1b07fea4977fb61d`，现仅作历史记录。

### 更早候选（历史）

2026-10-07 在提交 `bbe44511e0acf5ae1365eb4727ab34c1b892e33c` 执行 `bash test-plan/issue-66-run.sh local`，证据目录基名为 `issue66-gate2-candidate.Sw2XGr9j`。`candidate-result.json` 记录 `evidence_validity=VALID`、`overall=PASS`、退出码 `0`、`runner_execution=COMPLETE`、`local_product_failures=[]`、`gaps=[]`；样例账本为 `VALID`，`sample_ledger_exit_code=0`，`combination_check_exit_code=0`。七套件全部通过，共 199 项：`judge` 114、`execution_wiring` 14、`structured_result` 11、`credential` 17、`local_state` 12、`validation_handoff` 22、`agent_contract` 9。`candidate-result.json` 的 SHA-256 为 `91e23821c5567b4876d6f13cd77e3a8b6692c88818a5c2c85c0ddb50f723bb28`；`suites.jsonl` 的 SHA-256 为 `5369e3b7b2e04a29769532b9b2b9b20ad3d442285692b6f5a47ff5ce6318573b`。该轮仅作历史记录。

### 更早一轮候选（历史）

此前执行 `bash test-plan/issue-66-run.sh local`，证据目录基名为 `issue66-gate2-candidate.RGFhzJ3R`。`candidate-result.json` 记录 `evidence_validity=VALID`、`overall=PASS`、退出码 `0`、`runner_execution=COMPLETE`、`local_product_failures=[]`、`gaps=[]`；样例账本为 `VALID`，`sample_ledger_exit_code=0`，`combination_check_exit_code=0`。七套件全部通过，共 199 项：`judge` 114、`execution_wiring` 14、`structured_result` 11、`credential` 17、`local_state` 12、`validation_handoff` 22、`agent_contract` 9。该证据记录的基线提交为 `2723996424c6485fb61efcb4808a8e55c1d71cdd`，并如实记录了当时的工作树修改；这些修改已提交并推送。交接目录修复回归通过；代理约定只记录该轮通过结果，不推断此前失败的具体修复原因。此前来源 `2497dae2fffc02b0a66d33ea33b0405e128a9154` 的证据目录基名为 `issue66-gate2-candidate.vno2ISAS`，结论为有效 `FAIL`、退出码 `1`，作为历史保留；不在此重复其临时目录绝对路径。软件版本或摘要即使记录，也只作来源定位。

## 安装和预检入口

正式包装器删除 Python 次版本限制，并把其余参数原样交给执行器。执行器要求本次产品来源 `--product-source`、夹具根目录和独占证据目录；包装器本身补充当前仓库路径。运行环境准备者提供本次实际的 APM 远端来源选择器、夹具根目录和独占证据目录：

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

每次使用从未存在的独占证据目录。产品只通过受支持的 APM 远端来源选择器安装；本地路径、符号链接、可编辑安装、复制产物和手工补丁均不符合共识，执行器必须在运行安装命令前拒绝本地来源。记录实际产品来源选择器、实际测试和夹具来源、安装命令、工作目录、工具及模型配置、执行编号、每条命令及原始输出和退出码。来源、版本或未提交状态差异本身不拒绝执行；不得使用软件文件摘要或锁文件版本代替业务证据。

### 本轮 R7 预检结果

2026-10-07 曾完成的预检证据集编号为 `issue66-r7-preflight-now-45b81f3`，其输入来源是 PR 提交 `0896243702c959da8e4981bffacfe820b06719b6` 的干净源码归档。复核原始 `install.json` 发现 `requested_product_source` 是本地绝对路径，`product_source_kind` 和安装详情均为 `local_project`，安装命令使用 `--root <consumer>`。尽管退出码为 `0`、锁文件可解析且安装器报告装入 10 个依赖，该方法违反本地共识，不能作为受支持安装路径或有效预检通过证据；此轮只保留为历史记录。

随后针对 PR 提交 `e7d6c7ab4adafddff2aa69f83070892e17d504b6`，使用 APM 远端提交选择器进行了两次预检：`issue66-r7-preflight-pr73-e7d6c7a-20261007-122605` 与 `issue66-r7-preflight-pr73-e7d6c7a-20261007-122605-retry1`。两轮均为 `CASE_NOT_STARTED`、`formal_request_sent=false`。APM 已解析该精确提交并开始安装；依赖仓库克隆遇到 GitHub HTTPS TLS 连接提前结束，安装命令退出码为 `1`，安装事务未提交。两轮均未生成成功的安装或预检记录；原始命令输出和判定保留在各自证据集中。

按用户要求再次重试，第三轮安装命令使用远端选择器 `ScholarWorkflow/professor-contact#e7d6c7ab4adafddff2aa69f83070892e17d504b6`，证据集为 `issue66-r7-preflight-pr73-e7d6c7a-20261007-retry2`。命令在 1200 秒后超时；超时记录没有保存 APM 的提交解析输出，也没有生成成功的安装或预检记录。判定为 `CASE_NOT_STARTED`、`formal_request_sent=false`。这三轮尝试均未完成；当时尚无符合共识的预检结果。第三轮的超时判定与原始输入记录保留在该证据集中。

2026-10-07 针对 PR 当前提交 `7ddd4a6eaaf50e718e40a1099989bded747b0c60` 执行第四轮预检。证据集为 `issue66-r7-preflight-pr73-7ddd4a6-20261007-210516`；`install.json` 记录 APM 远端提交选择器安装通过、退出码 `0`、已安装提交与请求提交一致、消费者为新建且 `manual_patch=no`，锁文件解析通过。`fixture-pre.json` 及运行前快照检查均通过。执行器来源提交为 `d07132f419b2019e243e86a0793800dba0fb5004`。`preflight.json` 记录 `classification=PREFLIGHT_ONLY`、`formal_request_attempted=false`、`formal_request_sent=false`，安装、初始输入、请求构造和运行前快照均已准备。此次远端安装预检完成；没有发送正式请求或运行 `/eval`。

此前的失败尝试也保留为历史：首次预检发现预检模式误读 `EVAL_PORT`，现已改为只有正式模式才读取端口，并增加接线回归；提交 `2723996424c6485fb61efcb4808a8e55c1d71cdd` 的尝试，以及提交 `45b81f3458dbeb5ed3ea5855823cc0cef19ed509` 的普通 HTTPS、HTTP/1.1 重试，均因 GitHub 依赖下载中断而未完成。上述本地路径预检不能替代通过远端来源选择器的预检；各轮原始命令和输出保留在各自 `commands` 目录。

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

## R20 固定 Stage-3 写入：候选执行步骤（未执行）

本节对应唯一候选计划 `issue-66-test-plan-r20-stage3-write-validation-r8-2026-10-08`，以已批准 Issue #66 实施计划 r15 为需求基线。它只补充新固定写入命令的定向本地证据步骤；R7 下文所列 `PASS` 是历史结果，不是 R20 当前结果。Gate 2 为 **pending、未批准**，Gate 3 未运行；正式 `/eval` 未获批准且未运行。本轮没有执行本地测试或候选运行器。

### 允许形成的定向本地证据

新鲜 `plan_reviewer` 审核通过并由负责人确定测试入口后，才可在仓库根目录运行以下两个定向命令。不得用旧七套件结果替代它们，也不得在当前候选审核前运行完整 `issue-66-run.sh local`：

```sh
(cd .apm/skills/professor-contact/tests && \
  uv run --no-project python -B -m unittest -v test_issue66_stage3_write_validation)
```

```sh
(cd .apm/skills/professor-contact/tests && \
  uv run --no-project python -B -m unittest -v \
    test_stage3_idea_generator_agent_contract.Stage3IdeaGeneratorAgentContractTests.test_fixed_writer_contract_and_caller_stop_before_save_on_error \
    test_stage3_idea_generator_agent_contract.Stage3IdeaGeneratorAgentContractTests.test_validator_without_output_file_remains_read_only)
```

每条命令须在独占证据目录保存完整命令、仓库根和实际工作目录、产品与测试来源、候选计划修订号、工具版本、逐项 unittest 身份及结果、原始 stdout、stderr 和退出码。记录结果时不得预设通过数；测试身份来自实际 unittest 输出，输出解析失败或命令未完整运行应判证据无效，而不是测试通过。

### 写入成功证据要求

回归材料须能复核 validator 完整结果对象的原始参数值：`result=ok`、完整 `files[]` 与 `notes`，并保留每个条目的候选稿路径、`artifact`、`verdict`、`blocking`、`minor`、`issues` 和 issue 字段。真实 prepare 集成用例须从 `stage3-prepare-validation` 实际返回的 `output_file` 取路径，并把同一个完整 JSON 字符串原样作为 `--result-json` 的单一参数传入。成功事实必须以原始字节核对：固定入口退出码为 `0`，stdout 非空；单文件 stdout 与指定文件完全相同，批量每个输出文件均与同一 stdout 完全相同；解析后所有文件都包含相同完整对象及扩展字段；输出权限为 `0600`。不允许仅比较解析后的对象来代替字节相等证明。

单文件命令只能提供 `--output-file`；批量命令只能提供 `--output-map-json` 和同一个完整 `--result-json`。批量映射要逐路径覆盖全部候选项一次，且候选与输出路径均唯一、绝对。正式运行证据必须把 validator 的完整返回对象、prepare 返回的每个输出路径、writer 实际 argv、writer stdout 与文件原始字节、权限、save/record 实际路径及顺序绑定到同一轮。缺少任一关联时只能判证据无效或阻断；不得把缺证据算作通过。未提供 `output_file` 的验证器分支必须保持只读，静态代理回归需锁定此要求。

### 拒绝、冲突和失败副作用证据要求

无效结果或映射必须记录完整错误 stdout、非零退出码以及每个目标文件调用前后状态。要求覆盖顶层及字段类型错误、重复键、非有限数字、缺少必需字段、未知 `artifact`/`verdict`、非法严重级别、缺失或不完整 issue、非法位置、超长引文、无候选条目、计数/verdict 不一致、映射缺漏/重复/额外项/字段错误、重复输出路径、单文件相对输出路径和输出父目录不存在；拒绝时不得生成输出文件，也不得创建父目录。已有文件、符号链接及链接目标保留调用前原始字节；批量中任何目标冲突都必须在第一次写入前拒绝，`completed_paths` 为空。

第二个批量目标部分写入失败时，应保留第一个完整文件并记录为已完成，只移除本次创建的不完整第二个文件；不得删除第一个成功文件。调用者遇到非零退出、结构化 `error`、缺失或不完整 stdout、stdout 与文件字节不一致时，必须在写入下一阶段状态前停止：不运行 `stage3-save-validation`、`stage3-record-validation`、修正轮或新 generator，不从错误输出重建正文。

### Gate 2 / Gate 3 停止条件

本候选当前未具备 Gate 2 所需的原生观测能力。现有 `judge_issue66_stage3_runtime.py` 把 `contact_state.py stage3-write-validation` 判为未知行为；`fileChange Add` 事件没有排他创建或权限位；`issue66_execution.py` 的快照不包含临时 handoff 文件及权限。只把正式执行器 `PLAN` 改为 R20 不能修复这些缺口。Gate 2 审核前必须先由本地测试工程师更新事件采集、输出文件快照和判定器，并新增正例、产品违反负例及缺关联证据负例。所需关联是同一轮 validator 完整返回值 → writer 完整 argv → prepare 返回路径 → writer stdout/原始文件字节/文件模式 → save/record 路径和顺序。若原生事件源无法提供任一事实，须调整证明方式或保持 Gate 2 不批准。

能力预检须先于 Gate 2 审核完成，使用 R20 `PLAN` 的正式执行器 `preflight` 模式，禁止发送 `/eval`。预检应从实际安装源执行固定 writer 的受控本地调用，保存真实命令参数、进程退出码、stdout 原始字节、输出文件原始字节、实际文件模式和调用前后路径状态；同时验证正式事件采集器能把命令、prepare 输出路径及后续保存路径关联到同一轮。预检产物须含原始事件和解析后的字段，能分别给出通过、产品违反、证据缺失/阻断、执行无效四种可区分结果。不得以手工构造的事件、旧 attempt #11 或旧 R7/R19 运行结果替代。当前采集器和判定器尚未更新，因此此预检尚不可执行；计划审核不能把它留待 Gate 2 批准后才处理。

新鲜审核者检查计划和前置核验通过后，才可运行列出的本地定向用例。无论本地用例结果如何，本节均未授权 Gate 2、Gate 3 或正式 `/eval`。

历史正式尝试 #11 保持 `INVALID_TEST_EXECUTION`。所引历史记录不能证明 writer 实际写入为零字节；可确认的是入口绑定无效、事件缺号、writer 生产范围不能归因，因此没有产品通过或产品失败结论。不得重跑或把它当成本候选测试证据。正式 `/eval` 只能在 Gate 2 审核明确批准后另行决定，且依照既有一次请求限制执行。
