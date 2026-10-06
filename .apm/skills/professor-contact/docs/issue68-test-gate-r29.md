# 第 72 号拉取请求：测试计划第 25 版测试实现与正式执行步骤记录

记录编号：`issue68-r29-r25-full-procedure-2026-10-06`。

**状态：第二关口未完成，PC68-R1 不得启动。** 本文固定 PC68-R1 的步骤、证据、判定、停止条件和复验依赖；不代表测试实现已审核，不是正式验收结果。本地合成采集预检已完成，但真实 `app_server` 采集和正式线程关联仍未核实；PC68-R1 未运行。

## 1. 权威版本与当前绑定

| 项目 | 固定版本或状态 |
| --- | --- |
| 当前测试计划 | `issue-68-test-plan-r25-2026-10-06`，PR #72 评论 [6010481027](https://github.com/ScholarWorkflow/professor-contact/pull/72#issuecomment-6010481027) |
| 被替代计划 | 第 24 版，PR #72 评论 [6009207405](https://github.com/ScholarWorkflow/professor-contact/pull/72#issuecomment-6009207405)；第 25 版完整取代它，不拼接旧版 |
| 第一关口验收约定 | `issue-68-gate1-r4-2026-10-05`，第 68 号议题评论 `5981562292` |
| 获批产品方向 | `issue-68-plan-r13-2026-10-06`，第 68 号议题评论 `6000673923`；范围批准见 PR #72 评论 `6000931583` |
| 被测产品目标 | `ScholarWorkflow/professor-contact@b39a4252e3ce473f8cdeedd2e12b0cf86d6f597d` |
| 测试改动前基线 | `ScholarWorkflow/professor-contact@1c5023decdcfb22b5d196bf22640b3dab45a7b99` |
| 新增测试实现提交 | `f08474bfb73389488a462619ae9a0913fc8338b0` |
| 运行证据契约 | `.apm/skills/professor-contact/tests/runtime/issue68-runtime-evidence-contract-r19.json`，契约修订 `issue-68-runtime-evidence-r29-2026-10-06` |
| 共享测试资产参考版本 | r25 读取时记为 `c738fa2f8bcbb16cd99d741332d5f59b062b6357`；当前实际检出位置与版本尚未核验 |

r25 指定观察教授原有 `owner_input_file` 解析所得对象，并由同一对象驱动原业务调用。固定捕获器在教授正常解析后只读保留对象，用该对象生成实际 `stage5-plan` 参数，再将真实参数、原始标准输出、结构化结果及退出码写入同一命令输出。verifier 还核对固定捕获器源码和独立 `commandExecution.command`。正式运行时，适配器的运行代次、根子线程关系、教授线程身份及命令编号将把这份读取记录关联到本次分配；合成预检只证明本地捕获路径可用，不冒充正式运行证据。

观察实现和合成预检已完成，现有阻断是第二关口审核未通过、候选尚未冻结。r25 要求第二关口先审核固定实现并指定唯一完整版本，因此在审核完成前，PC68-R1 不检查评估服务、不安装消费者、不发正式请求。正式线程、服务、模型及环境事实留待获批候选的一次正式运行采集。

## 2. 用例、输入和范围

正式用例仍只有 `PC68-D1` 与 `PC68-R1`，不增加用例。本记录定义 `PC68-R1`；`PC68-D1` 的历史证据处理见第 9 节。

`PC68-R1` 使用两位姓名不同的教授及其独立本地邮件包、合法显式选择、一条无关选择行、一个坏包和现有的缺少核验前提。准备阶段只建立测试所需本地状态、输入文件和独立预期，不预先代替根代理分配选择，不生成可冒充本次根代理结果的教授交接文件或分教授选择包。根代理必须在本次正式运行中自行发现输入并只分配一次。

本例验证第五阶段本地事实来源、逐教授隔离、确定性分配和原值保持、正式委派与结果消费、缺少核验时的合法停止以及独立总览。不得扩展到前四阶段、网页研究、邮件生成、人性化改写、后续选择读取、渲染、提交或业务校验。后续选择读取和包装转交的确定性事实由 `PC68-D1/P7` 负责。本次运行没有发生的活动必须如实标为未测试，不能要求越过核验保护，也不能声称已证明。

以下具体输入值尚未记录，执行前必须逐项写入记录并从获准来源核对：教授目录原值、邮件包路径、邮件编号、原始选择行及预期分配、无关行、坏包内容、缺核验状态、本地状态初始值和前置文件校验值。不得用此处的描述代替实际值或从当前产品输出反向构造预期。

## 3. 执行前必填的输入与环境值

计划记录的六项运行事实为实际 `model`、`executor`、`entrypoint`、`isolation`、`shared assets` 和 `service version`。`model` 来自同次请求的 `--model`；`executor` 来自实际 Codex dispatch 分支的 `base.codex_host` 函数/模块身份及 dispatcher、runner 源文件 SHA-256；`entrypoint` 来自干净消费者内已安装 `contact_state.py` 的路径和哈希；`isolation` 来自服务请求前后只读快照；`shared assets` 来自 producer/fixture 干净 SHA 和锁文件哈希；`service version` 来自服务请求前后只读取得的版本。当前这些本次运行值尚未采集；不得猜测或用旧运行代填。Gate 2 未完成时先记 `CASE_NOT_STARTED`，不查询、安装、检查或请求评估服务。Gate 2 完成后再按下表采集；任一必填事实缺失或版本不符时，不发正式请求。

| 运行事实 | 记录方式与来源 | 当前状态 |
| --- | --- | --- |
| `model` | 从本次唯一请求的 `--model` 记录实际模型 | 尚未采集；PC68-R1 未运行 |
| `executor` | 记录实际 Codex dispatch 分支的 `base.codex_host` 函数/模块身份，以及 dispatcher 和 runner 源文件 SHA-256；不包括 eval-server listener 或 host ID | 尚未采集；PC68-R1 未运行 |
| `entrypoint` | 记录干净消费者内安装的 `contact_state.py` 路径和 SHA-256；正式入口整体为评估服务加干净消费者 | 尚未采集；消费者未安装 |
| `isolation` | 比较服务请求前后只读快照中的存储隔离事实 | 尚未采集；服务未读取或请求 |
| `shared assets` | 从 producer/fixture 的干净 SHA 和 `apm.lock.yaml` 哈希记录 | 尚未采集；实际资产检出未核实 |
| `service version` | 请求前后只读取得服务 `git rev-parse HEAD`，通过既有 `clean_revision` 校验并确认 `same_service`；不硬编码 eval SHA。listener 信息单独保留在 `eval-service-provenance.before/after.json` | 尚未采集；服务未读取或请求 |
| 产品检出 | 产品仓库路径、干净状态、完整提交号；必须等于 `b39a4252e3ce473f8cdeedd2e12b0cf86d6f597d` | 当前正式运行环境未核验 |
| 测试实现 | 唯一候选完整提交号、入口与判定程序版本；须在第二关口审核后冻结 | 本轮候选 SHA 为 `f08474bfb73389488a462619ae9a0913fc8338b0`；此 SHA 待审核，不表示获批或正式运行通过 |
| 输入与预期 | 第 2 节逐项列出的真实测试值、来源、前后文件状态及独立预期 | 未知 |
| 运行路径 | 空输出目录、消费者目录、证据归档目录及互不重叠证明 | 未知 |

服务 listener 信息仅记录在 `eval-service-provenance.before/after.json`，不归入 `executor`。主机、适配器、进程号和端口可以作为诊断信息保留，但不是独立必填项。r25 没有指定固定 eval-server SHA；服务版本须从本次服务请求前后只读快照取得，并经 `clean_revision` 校验及 `same_service` 比较。Gate 2 完成后才读取这些快照；本记录未触碰服务，也不声称环境隔离已满足。

## 4. PC68-R1 固定步骤、输入来源与直接证据

步骤按表中顺序执行。任何前置门未通过即停止，不得跳到下一步。PC68-R1 只允许一次正式服务请求，不重试，不更换模型、执行器、服务或入口来寻找成功。

| 步骤 | 操作和实际输入来源 | 必须保存的直接证据及核对条件 | 停止条件 |
| --- | --- | --- | --- |
| 0. 冻结与准入 | 使用唯一完整测试实现版本、获批产品目标和 r25 完整记录；完成第二关口审核及第 5 节最小观察预检 | 审核指定版本、产品与测试完整 SHA、入口及判定程序版本；确认正式入口类别未改，产品代码未为测试修改 | 第二关口未完成时先记 `CASE_NOT_STARTED`，且不查询、安装、检查或请求评估服务；候选 SHA 未固定、预检不通过或任一必填事实未知时也不启动 PC68-R1。当前状态即为此门未通过 |
| 1. 准备输入 | 建立两位教授独立本地包、合法显式选择、无关行、坏包与缺核验状态；保存独立预期。不得提前分配、拆分选择或制作教授交接文件 | 每个原始输入的来源、路径、内容校验值；教授目录和邮件编号原值；本地状态及隔离目录的执行前快照；输入之间不重叠的证据 | 输入不完整、预期并非独立于被测输出、目标或目录冲突、准备阶段写入根代理交接/分配结果：停止并修复测试准备，不运行正式请求 |
| 2. 检查安装和隔离 | 仅在第二关口完成后，按固定产品提交支持的安装方式建立干净消费者；记录其 `contact_state.py` 路径和哈希；记录 Codex dispatch 身份及源文件哈希；通过只读请求前快照记录服务版本和隔离；检查空输出目录 | 产品及消费者版本、安装入口路径和哈希；dispatch 函数/模块身份与 dispatcher/runner SHA-256；目录为空且彼此不重叠；服务请求前 provenance 快照 | 第二关口未完成时不得进入本步骤或触碰服务；安装失败、产品版本不符、目录不干净或隔离不成立：`CASE_NOT_STARTED`；不得直接运行命令行工具替代入口，也不得启动或重启评估服务 |
| 3. 发送唯一正式请求 | 通过评估服务和干净消费者组成的正式入口执行本次固定请求；使用第 3 节记录的模型、Codex dispatch、已安装 `contact_state.py` 入口及请求前服务版本 | 请求与响应原件、根线程和运行标识、请求次数、入口日志；确认恰好一次请求 | 任何前置配置改变或服务不可用时不发送；请求一旦发送，不重发完整业务请求。服务、权限或模型问题按实际外部阻断保留 |
| 4. 根代理发现 | 根代理通过原有只读发现路径检查本地包；坏包不得影响合法教授包 | 正式根线程的 `commandExecution` 调用编号、实际线程、运行代次、事件顺序和 `aggregatedOutput`；输出应区分两位合法教授与坏包，且发现不带 `--emit-choices-scope` | 输出缺失或不能归属时按证据缺失/无效分类；真实有效输出显示业务越界时判产品失败 |
| 5. 根代理分配 | 根代理在正式根线程上恰好成功调用一次 `stage5-partition-choices`；只处理本次请求输入 | 调用的线程、运行代次、`commandExecution.id`、参数及真实 `aggregatedOutput`；完整分配行中的教授目录、包、目标和所有选择字段与第 1 步独立预期逐字段相同；分配完成事件先于任一教授业务调用 | 零次或多次成功根分配、分配由教授线程执行、分配结果错配或任一教授业务早于分配完成：有直接有效证据时 `FAIL_PRODUCT`。没有支持的调用观察时不得推断产品行为，按阻断或无效证据处理 |
| 6. 正式委派 | 根代理按两位教授分别委派；线程身份只采用共享适配器确认的正式 `spawnAgent` 关系 | `dispatch.thread_relations` 中 `tool=spawnAgent` 且 `sender_thread_id` 为根线程的两条正式边；线程 ID 与运行代次。以同次 `subAgentActivity` 唯一绑定 `agentThreadId` 到 `agentPath`；`agentPath` 只作回执关联键 | 没有正式关系但运行未证明实际调用时不得宣称委派故障；缺少受支持线程关系为 `BLOCKED` 或 `NOT TESTED`，按实际停止原因说明。单一 child 被多个不同 path 绑定为 `INVALID_TEST_EXECUTION` |
| 7. 教授交接与实际读取 | 根代理在本次运行中生成各自 `owner_input_file`。各教授代理沿原有正常路径解析自己的 JSON；固定捕获器只读复制该次解析所得对象，后续业务参数继续取同一个对象 | 每次本地捕获信封含 `pc68_fixed_capture`、`pc68_actual_input_observation`、`stage5_invocation`、`stage5_raw_stdout`、`stage5_process`、`stage5_plan`、`return_code`。同一 `capture_id` 关联本地读取、实际 CLI `argv`、stdout/stderr 摘要和退出码；verifier 从独立 `commandExecution.command` 校验固定捕获器的精确调用路径/参数，脚本摘要从固定仓库源码校验。另关联 `runtime_generation`、正式教授 `thread_id`、`commandExecution.id`、教授目录、`source_step=owner_input_json_parse`、`business_step=stage5-plan` | 整个 `stage5_invocation` 缺失为 `BLOCKED_OBSERVABILITY`；对象存在但必需 `argv` 缺失或损坏为 `INVALID_EVIDENCE`。字段关联不一致、捕获器调用不符或运行/线程/调用关联歧义为 `INVALID_EVIDENCE` |
| 8. 首次计划与数据边界 | 同一教授、同一解析对象驱动原有 `stage5-plan`；本例首次调用不带 `--result` 或 `--choices`。业务程序必须是消费者内正式程序 | 同一 `commandExecution` 中实际 `stage5_invocation.argv` 完整字符串数组、`stage5_raw_stdout`、与其一致的 `stage5_plan` 结构化结果及 `return_code`；按原字段检查 `email_pack`、`emails`、`jobs[].model_input`、核验状态。将读取对象与本次根分配对应项、本地包独立预期逐字段比较，并检查没有兄弟教授数据、改写路径或编号 | 有效实际证据证明错包、错编号、选择错配、兄弟数据、`--choices-scope` 或首调含 `--result`/`--choices`：`FAIL_PRODUCT`。只有命令文字出现参数不能证明实际调用参数。核验证据要求早停时不得执行后续选择读取、重规划、渲染、提交或校验 |
| 9. 教授结果与根消费 | 根代理等待并分别消费正式教授线程真实返回；每位教授结果独立保留 | 正式 child 自身线程的原始最终结果；同一运行、当前 root turn 的 `rawResponseItem/completed` `agent_message` 回执；`recipient=/root`、`author` 等于唯一 `agentPath`，正文为规定的 `Message Type: FINAL_ANSWER`、`Task name: /root`、`Sender: <path>`、`Payload:` 和唯一顶层 JSON。Payload 顶层含 `professor_dir`、`status`、`reason_code`；回执 `runtime_seq` 是消费点 | child 无 path 或无合法回执为阻断；多个不同 outcome 或 path 映射歧义为无效证据；合法回执与 child 自身结果不一致为 `FAIL_PRODUCT`。`child_thread_reads`、等待消息、完成诊断、角色自述和身份诊断均不能代替消费回执 |
| 10. 总览和最终消息 | 根代理消费完两位教授结果后，在根线程独立调用一次 `stage5-rebuild-overview` | 唯一总览调用的 `commandExecution.aggregatedOutput` 是结果唯一来源；开始顺序晚于每个正式教授结果消费点。当前根线程最终 `final_answer` 分别原样报告每位教授结果及完整总览结果；对象按业务字段识别，不要求固定包装键 | 提前或重复总览调用、改写教授结果、漏报或改写总览、结果双重归属冲突：有效证据证明时为 `FAIL_PRODUCT`。输出缺失为观察阻断，损坏/冲突/无法唯一归属为无效证据 |
| 11. 后置检查与清理 | 请求结束后检查本地状态、传递文件和服务隔离；只清理本请求临时数据 | 本地状态前后快照、相关文件内容/校验值、临时文件创建和清理事件；证明没有跨教授写入、总览反向修改教授结果，观察副本在原文件清理后仍可复查；请求后服务 provenance 与请求前一致 | 服务进程或存储隔离变化、证据被污染或不能归属为无效执行；真实跨教授写入为产品失败。清理不能删除其他请求数据，清理错误不得改写教授结果 |

正式线程集合只由共享适配器 @16 的正式 spawn 关系确定。`subAgentActivity` 不能创建或升级线程所有权；`requested_role`、加载身份、诊断事件及提示词内容均不构成正式归属证据。最终根消息仅选当前运行、当前根线程、当前 turn 的唯一 `final_answer`；不能从其他线程、旧 turn、评论阶段、历史输出或嵌套诊断补缺。

## 5. 正式运行前必须完成的观察预检

**当前门状态：第二关口未完成，PC68-R1 不可启动。** 合成捕获预检证明固定捕获器能将一次解析所得对象、同一对象生成的 CLI 调用和结构化输出关联起来；正式运行关联仍未采集。当前候选须先经过第二关口审核并冻结，之后才按固定步骤检查服务、安装消费者及记录正式运行事实。

四项必要预检为：入口可执行、消费者与服务及输出隔离、所需证据可取得且能关联到本次运行/调用/教授、判定能区分合法输入、产品错配、缺失与损坏证据。这里的观察能力检查是最小非验收检查，不是 PC68-R1，也不运行完整教授业务。

观察能力预检必须用合成 JSON 输入，通过普通命令工具的标准输出，实际验证以下完整路径：

1. 用固定捕获器对合成 `owner_input_file` JSON 只解析一次；在原解析路径只读复制实际解析对象，记录输入字节摘要、对象摘要和读取次数。
2. 让原有 `stage5-plan` 使用该同一个内存对象执行只读计划；不经第二次文件读取、不复制一份预期对象充当解析结果，也不更换业务入口。
3. 在发起原 `contact_state.py` 子进程时，由固定捕获器实际捕获完整有序 `argv`、原始标准输出、标准错误摘要及退出码；不从 shell 命令文字还原参数。
4. 将上述值装入单个严格 JSON 信封。verifier 从独立 `commandExecution.command` 字段核对精确捕获器路径和参数，并从 runner 创建的 manifest 核对动态消费者目录；捕获器摘要从固定仓库源码取得，不接受信封自报替代。
5. 对照 `runtime_generation`、正式教授线程、`commandExecution.id`、教授目录、来源步骤和业务步骤，证明本地捕获信封唯一对应这次读取和调用。重复调用分别产生、分别检查信封。
6. 执行合法读取后清理、前序来源与实际读取不一致、错误教授/目标/业务值、仅有命令文字、无关读取、事后读取、缺失观察、格式损坏和关联歧义等合成反例。验证格式/归属错误与产品输入错配分别分类，且观察不改变业务对象和参数。
7. 保留合成输入、普通命令、原始标准输出、原始事件、判定输出、版本及校验值；清理临时源文件后，仍能用保存副本完成判定。

当前已知的判定边界：合法读取后清理仍应认可已保留的同次证据；前序分配与实际读取错配或首次计划真实返回错误包、编号、业务数据或兄弟数据应为 `FAIL_PRODUCT`；整个 `stage5_invocation` 字段缺失为 `BLOCKED_OBSERVABILITY`；字段对象存在但必需 `argv` 缺失或损坏为 `INVALID_EVIDENCE`；信封及关联损坏或歧义为 `INVALID_EVIDENCE`。固定捕获器将单次解析、同次 CLI 和原始输出关联起来；正式 app_server 事件须在 PC68-R1 中与运行代次、教授线程及调用编号关联。命令文字、无关打印、无关读取和事后文件不能作为实际输入证明。

合成采集预检新结果见本节下方。本轮完整 `test_issue68_runtime_r19.py` 共 19 项，全部通过；契约格式检查只证明 JSON 可解析，不扩大本次预检证明范围。合成捕获验证通过不等于正式入口观察预检通过。

### 本地合成采集预检结果

采集预检使用本地合成 `schema=3` 邮件包和模板，真实调用产品 `contact_state.py stage5-plan`，不是 PC68-R1。原始 CLI 退出码为 `0`；结构化输出为 `status=ok`、一个 `email_id`、一个邮件 job 和一个 `jobs[].model_input`，并含 `verify.合成教授=needs_recheck:missing`。这证明该合成输入下真实本地 CLI 产生了只读计划输出，不是正式教授数据或业务结果。

runner 的 `_synthetic_capture_preflight()` 将 stdout 和 manifest 落盘后重新读取，再交给判定程序，返回 `verified=true`、`reason=null`。这只说明合成捕获本身可验证；正式入口因第二关口未完成返回 `CASE_NOT_STARTED`，不会检查服务或发送请求。证据文件为：

| 证据 | 路径 | 说明 |
| --- | --- | --- |
| 采集预检 manifest | `.apm/skills/professor-contact/tests/runtime/evidence/issue68-r29-synthetic-capture-preflight.json` | 记录合成输入、一次读取、实际 `argv`、CLI 退出码与结构化输出、普通 stdout 采集方式及合成关联标签；并记录评估服务未调用、正式请求未发送、正式用例未开始 |
| 普通命令 stdout JSON | `.apm/skills/professor-contact/tests/runtime/evidence/issue68-r29-synthetic-capture-stdout.json` | 保存 `pc68_fixed_capture`、`pc68_actual_input_observation`、实际 CLI `stage5_invocation.argv`、`stage5_raw_stdout`、`stage5_process` 摘要、同次 `stage5_plan` 结构化结果和 `return_code=0` |

两个受跟踪的合成 JSON 在固定捕获器和 verifier 验证后，将机器本地绝对路径替换为 `/__pc68_*__/` 占位路径以便移植；manifest 另存路径替换前 stdout 与解析对象的 SHA-256。它们保留捕获关系及原值校验摘要，不包含本机路径。

预检脚本从固定捕获器进程的 stdout 管道读取结果并保存为合成证据。manifest 记录 `owner_input_read_count=1`、`producer_return_code=0`、`eval_service_called=false`、`external_request_made=false`、`formal_case_started=false`。关联值 `runtime_generation=synthetic-r29-fixed-capture-preflight`、`thread_id=synthetic-professor-thread`、`commandExecution_id=synthetic-command-fixed-capture` 都是合成值，不是 `app_server` 的真实运行代次、正式线程或调用编号。

契约格式检查命令：

```sh
jq -e . .apm/skills/professor-contact/tests/runtime/issue68-runtime-evidence-contract-r19.json >/dev/null
```

结果：通过。

定向检查完整命令：

```bash
UV_CACHE_DIR=/tmp/pc68-uv-cache uv run --no-project python -m unittest discover -s .apm/skills/professor-contact/tests -p test_issue68_runtime_r19.py
```

本轮实现提交 `f08474bfb73389488a462619ae9a0913fc8338b0` 上，定向检查 20 项通过，结果 `OK`。无 `FAIL_PRODUCT` 的混合聚合断言包含 `CASE_NOT_STARTED` 子项，并确认该子项分类保留。合成采集预检还确认真实合成 CLI 返回 `status=ok`，runner 重读 stdout/manifest 后判为 `verified=true`、`reason=null`。这些检查只验证判定与本地合成观察路径，不是 `PC68-D1` 或 `PC68-R1` 正式验收。

实际 `model`、`executor`、`entrypoint`、`isolation`、`shared assets`、`service version` 尚未采集；真实 `app_server` 事件及正式教授线程关联也未核实。主机、适配器、进程号和端口不是独立必填项。契约为 `input_observation_gate.formal_run_allowed=false`、`reason_code=second_gate_incomplete`；runner 必须先返回 `CASE_NOT_STARTED`，不得读取或请求评估服务。实际文件中的 `eval_service_called=false`、`external_request_made=false`、`formal_case_started=false` 确认本次服务和正式用例均未运行。PC68-R1 仍未运行，第二关口仍为 `INCOMPLETE`。

## 6. 正式终态、机器标签和总体分类

r25 的六种正式终态分别用于每个正式 child。对每个 child 保留原始机器 `status`、`reason_code`、退出码和原始证据，并分别记录正式分类；不把各 child 状态折叠成一个总分类。退出码本身不能替代分类依据。

| r25 正式终态 | 机器标签或记录方式 | 适用条件 |
| --- | --- | --- |
| `PASS` | 该 child 原始机器状态 `PASS` | 该 child 负责的全部事实都有直接、有效、可归属且一致的证据；合法核验早停后的后续业务事实不在本次证明范围内，不能假称已发生 |
| `FAIL` | 该 child 原始机器状态 `FAIL_PRODUCT` | 有效、直接证据证明该 child 的产品行为违反冻结要求，如实际输入错配、兄弟数据、路径/编号改写、越序分配、错误回执消费、总览早于结果消费或改写结果 |
| `BLOCKED` | 该 child 原始机器状态 `BLOCKED_OBSERVABILITY`，或保留外部阻断的原始机器状态和原因码 | 该 child 的事实因支持的观察条件或外部服务、模型、权限等条件无法判断；没有有效证据证明产品失败 |
| `NOT TESTED` | 该 child 原始机器状态 `NOT_TESTED` | 该 child 声明路径没有实际发生且非产品违规、外部阻断或测试缺陷；例如合法核验保护阻止后续选择读取 |
| `INVALID_TEST_EXECUTION` | 该 child 原始机器状态 `INVALID_EVIDENCE` | 该 child 的输入、执行或证据被污染、矛盾、损坏或无法归属；已知设计缺口须在第二关口修正 |
| `CASE_NOT_STARTED` | 该 child 原始机器状态 `CASE_NOT_STARTED` | 该 child 未越过固定启动边界，如第二关口未通过、安装失败、版本不符或隔离检查未通过 |

以下证据细分不得互换：

- 整个 `stage5_invocation` 字段缺失，意味着必需调用观察缺失，机器状态为 `BLOCKED_OBSERVABILITY`，正式请求前停止。
- `stage5_invocation` 对象存在，但必需 `argv` 缺失或损坏，属于观察结构无效，机器状态为 `INVALID_EVIDENCE`。
- `argv` 被真实捕获且证明首次调用带有禁止的 `--result` 或 `--choices`，或真实结构化业务输出证明错包、错编号、业务数据错配或兄弟数据，属于 `FAIL_PRODUCT`。
- 只有命令文字含这些参数，不能证明实际 argv，也不能据此判产品失败；根据实际信封是整项缺失还是结构损坏，分别阻断或判无效。
- 没有正式线程关系证据，不单凭零条关系推断产品委派故障；缺 path 映射为 `BLOCKED_OBSERVABILITY/root_result_consumption_unobservable`，一个 child 对应多个不同 path 为 `INVALID_EVIDENCE/child_agent_path_mapping_ambiguous`。合法回执缺失为阻断，多份不同结果为无效，回执与 child 自身结果不同为 `FAIL_PRODUCT/root_receipt_payload_changed`。

六种正式分类彼此不设全序，不按严重程度把一个 child 的状态改写为另一个状态。对总体字段仅采用以下规则：只有至少一个 child 的原始机器状态被有效证据确认为 `FAIL_PRODUCT` 时，才将总体分类设为 `FAIL`；同时保留每个 child 自己的机器状态、原因码及正式分类。没有确证的原始 `FAIL_PRODUCT` 时，总体分类字段留空，不从 `PASS`、阻断、未测试、无效执行或未启动状态推导总体结果。此规则不允许用其他 child 缺证据或有歧义来降级已经确证的 `FAIL_PRODUCT`。启动边界、观察缺失、无效证据、外部阻断和合法早停仍按各自实际原因记录，历史机器标签不重分类。

## 7. 输入与结果的比较规则

根代理分配返回是本次分配实际输出；它必须与独立预期比较，但本身不代表教授收到或读取了分配。每位教授实际输入证明需连接下列四个对象：

1. 本次根代理真实分配输出中的对应教授项。
2. 根代理本次生成的该教授 `owner_input_file`。
3. 教授线程原有 JSON 解析动作同次复制的只读对象。
4. 同一命令调用中的真实 `stage5_invocation.argv` 和 `stage5_plan` 结构化输出。

`pc68_actual_input_observation` 采用 `issue-68-test-plan-r25-owner-input-v2`。`pc68_fixed_capture` 记录固定捕获源码摘要、一次读取的 owner 文件和解析对象摘要；`stage5_invocation` 和 `stage5_process` 用相同 `capture_id` 关联实际 argv、stdout/stderr 摘要及退出码；`stage5_raw_stdout` 是原始 stdout，`stage5_plan` 必须与解析该 stdout 得到的对象一致，`return_code` 是同次调用退出码。正式线程证据应保存在 `output.app_server_events.commandExecution.aggregatedOutput`，并关联 `output.runtime_generation`、正式线程 `thread_id`、`commandExecution.id`、教授目录和步骤名。合成预检不含这些正式运行事实；它们由一次获批候选的 PC68-R1 采集。

结构化选择按字段和值比较，不要求缩进、键顺序或换行一致；教授目录、包路径和邮件编号按原字符串比较，不可规范化后掩盖改写。命令文字、命令中的 JSON/Python 字面量、临时路径、准备阶段文件、manifest 预期值、事后重读文件、最终业务结果、教授自述、加密提示词及无关输出均不能替代实际输入证据。计划输出只证明它明确返回的真实字段；它不证明该调用没有返回或记录的数据。

## 8. 既有尝试和停止条件

当前只冻结步骤，不启动正式请求。以下情况在服务调用前停止：第二关口未完成、测试提交/入口未固定、产品或测试版本错误、环境必填值未核实、合成观察预检不完整、消费者安装失败、服务 provenance 不符、存储未隔离、输出目录非空或与其他目录重叠。此时保留原始检查，按 `CASE_NOT_STARTED` 记录具体原因。

发出唯一正式请求后不重试。模型/服务/权限等外部条件导致无法判定时，保存原始响应和实际原因并归 `BLOCKED`；程序缺陷、证据污染或矛盾归 `INVALID_TEST_EXECUTION`；有效直接业务证据证明违反要求则归 `FAIL`。合规核验返回不足时，按产品现有保护在该边界停止；不得为了收集更多数据移除保护、跑选择读取、渲染、提交或校验。保留所有旧尝试及原始标签，不用后来新增的观察方法回溯改写历史结果。

历史 PC68-R1 已知曾在根代理分配输入边界之前或期间停止的尝试，不能提供本次教授实际读取、结果消费或总览结果；具体机器标签、目录和调用记录须从原始运行包逐一读取。本记录不重判这些尝试，也不把零条线程关系单独解释为委派产品缺陷。

## 9. PC68-D1 固定配方、组件映射与历史结果

本节按当前完整测试计划 r25（[PR #72 评论 6010481027](https://github.com/ScholarWorkflow/professor-contact/pull/72#issuecomment-6010481027)）收录 `PC68-D1` 的固定配方。测试资产 `.apm/skills/professor-contact/tests/test_issue68_stage5_local_state.py` 文件头仍有旧计划版本文字；该注释不是计划来源。本节的要求和证明归属以 r25 为准，组件名称以当前测试入口与组件映射为准。

### 9.1 三类测试证据的边界

| 类型 | 入口与用途 | 证据边界 |
| --- | --- | --- |
| 非正式合成回归 | `uv --offline --cache-dir /tmp/issue68-uv-cache run python .apm/skills/professor-contact/tests/test_issue68_runtime_r19.py`；另有第 5 节的合成输入采集预检 | 验证判定程序和合成观察路径。不是 `PC68-D1`，也不是 `PC68-R1` 的正式结果。 |
| 正式确定性用例 `PC68-D1` | 本节固定的 `run_issue68_stage5_routing.py --case PC68-D1` 完整入口，只运行 P1—P7 组件 | r25 规定的当前目标产品正式确定性用例；不调用评估服务，不发送模型请求，也不证明真实委派和运行时结果消费。具体是否执行以该版本运行记录为准。 |
| 正式运行用例 `PC68-R1` | r25 规定的现有评估服务及干净消费者入口，使用当前编码执行器分支，唯一一次正式请求 | 证明实际根线程、教授线程、输入读取、结果消费及总览。不能由合成回归或 `PC68-D1` 代替。 |

`PC68-D1` 的正式身份由 `--case PC68-D1` 和完整确定性入口确定。该 runner 的 `--execution-kind` 默认值是 `preflight`，因此运行元数据会出现 `execution_kind=preflight`；这个字段不把 `PC68-D1` 变成非正式合成回归。

### 9.2 `PC68-D1` 固定命令与产物

从 producer 仓库根目录执行。命令中的 `<干净产品检出绝对路径>` 和 `<空证据目录绝对路径>` 须替换成真实路径；证据目录须为空，并与产品检出不相交。产品目标版本固定为 r25 指定的提交：

```bash
env UV_CACHE_DIR=/tmp/uv-cache-pr72 uv run python .apm/skills/professor-contact/tests/runtime/run_issue68_stage5_routing.py \
  --case PC68-D1 \
  --producer-root <干净产品检出绝对路径> --producer-sha b39a4252e3ce473f8cdeedd2e12b0cf86d6f597d \
  --output-dir <空证据目录绝对路径>
```

不要传入 `--execution-kind`、fixture 或评估服务参数；上述命令按固定入口运行。runner 在输出目录中生成：

- `provenance.json`：产品提交、干净状态、`manual_patch` 和 `execution_kind`。
- `case-started.json`：固定组件集合检查通过后开始用例时生成。
- `proofs.json`：P1—P7 各自的组件完整名称、执行数量和逐组件日志。
- `unittest.txt`：七个 proof 外层测试的完整日志。
- `final-verdict.json`：机器终态、原因码、外层测试数及跳过、失败、异常计数。

另在该次运行目录保存命令、起止时间、runner 退出码、stdout/stderr、`execution-record.json` 与 `proof-counts.json`；它们和 `output/` 下的 runner 产物共同构成可追溯运行记录。候选测试实现的完整 SHA 单独绑定在记录中，不能用产品 SHA 或记录文件 SHA 代替。

### 9.3 必要预检及完成判定

执行 `PC68-D1` 前固定并记录：

1. producer 检出为 r25 指定的 `b39a4252e3ce473f8cdeedd2e12b0cf86d6f597d`，工作区干净；runner 在执行前后各核验一次提交和干净状态。唯一候选测试实现 SHA 也须记入运行记录。
2. 按 r25 配方使用 `uv run`，运行环境满足计划注明的 Python `>=3.11`；从 producer 仓库根目录调用固定入口。
3. 输出目录为空，且与 producer 仓库根目录互不包含；入口通过精确七个外层测试方法的集合校验后才写入 `case-started.json`。
4. 按下表完整执行 43 个必需组件，P1—P7 各有且仅有一个 proof 负责；不只选跑单个 proof，不重复运行同一组件。
5. `PC68-D1` 不需要模型、真实委派、共享运行环境或评估服务预检。那些是 `PC68-R1` 的入口和运行记录内容，不得为 D1 触碰服务。

组件集合与预检来源：完整计划的要求及 proof 归属见上述 r25 评论；外层方法集合、组件列表与嵌套执行逻辑见 `run_issue68_stage5_routing.py`、`test_issue68_stage5_local_state.py`；各组件实现分别位于表中模块。执行者应核对这些固定来源和实际候选 SHA，不用合成回归的通过代替组件运行。

runner 必须发现恰好七个固定外层方法。集合变化为 `INVALID_TEST_EXECUTION/unexpected_test_set`；任何 skip、expected failure、unexpected success 或错误为 `INVALID_TEST_EXECUTION/incomplete_or_nonordinary_execution`；组件断言失败为 `FAIL_PRODUCT/product_assertion_failed`；七个 proof 与 43 个组件均以普通结果通过、且执行前后版本保持固定时，runner 返回 `PASS`。保留 JSON 机器回执、完整日志和组件列表；退出码单独记录，不能仅凭退出码替代回执。

### 9.4 P1—P7 与 43 个必需组件映射

下表组件名称与当前 `PROOFS` 映射逐项对应。`PC68-D1` 的外层 runner 仅发现七个 proof 方法；每个 proof 再运行表中对应组件。组件总数为 43（4+4+2+2+7+4+20）。

**P1 · R68-1、R68-6 · 4 项**（本地邮件包为唯一事实来源，不回退到全局包、不增加迁移或双读写）：

- `test_contact_state.TestStage5PerProfessorState.test_issue68_t68_1_local_pack_is_the_only_stage5_fact_source`
- `test_contact_state.TestStage5PerProfessorState.test_issue68_t68_1b_missing_local_pack_never_falls_back_to_global`
- `test_contact_state.TestStage5PerProfessorState.test_issue68_t68_1c_local_pack_must_prove_one_professor`
- `test_contact_state.TestStage5PerProfessorState.test_issue68_t68_2_legacy_global_pack_cannot_change_local_result`

**P2 · R68-2、R68-7 · 4 项**（定向邮件只处理目标，无关行不阻断；目标自身错误拒绝；校验仅限当前教授）：

- `test_contact_state.TestStage5PerProfessorState.test_issue68_t68_3_other_professor_files_never_gate_this_one`
- `test_contact_state.TestStage5PerProfessorState.test_issue68_t68_4_this_professor_stays_fail_closed`
- `test_contact_state.TestStage5PerProfessorState.test_issue68_unselected_malformed_local_row_is_noise`
- `test_issue68_choices_attribution.TestStage5ChoicesAttribution.test_issue68_r11_targeted_run_filters_unselected_explicit_rows`

**P3 · R68-3 · 2 项**（同教授整批处理；不合法时不得部分提交）：

- `test_contact_state.TestStage5PerProfessorState.test_issue68_t68_5_local_batch_covers_one_professor_only`
- `test_issue68_root_partition.TestStage5BatchStaysAtomic.test_r19_batch_with_one_missing_humanized_commits_nothing`

**P4 · R68-4、R68-7、R68-8 · 2 项**（教授间结果隔离；另一教授失败不回滚本教授；校验只更新命名状态）：

- `test_contact_state.TestStage5PerProfessorState.test_issue68_t68_6_second_professor_failure_keeps_first_commit`
- `test_contact_state.TestStage5PerProfessorState.test_issue68_validation_updates_only_the_named_local_state`

**P5 · R68-5 · 7 项**（总览由本地状态派生、人工编辑保护。`AD68-2` 的通用写锁归第 48 号议题，本用例没有该项组件）：

- `test_contact_state.TestStage5PerProfessorState.test_issue68_t68_7_finalize_never_touches_the_aggregate`
- `test_stage5_overview.TestStage5OverviewRebuild.test_issue68_t68_7_rebuild_joins_each_professor_local_state`
- `test_stage5_overview.TestStage5OverviewRebuild.test_issue68_t68_7_rebuild_is_deterministic_after_deletion`
- `test_stage5_overview.TestStage5OverviewRebuild.test_issue68_rebuild_never_reads_or_writes_shared_registry`
- `test_stage5_overview.TestStage5OverviewRebuild.test_issue68_t68_7_manual_aggregate_edit_blocks_only_the_rebuild`
- `test_stage5_overview.TestStage5OverviewRebuild.test_issue68_t68_7_malformed_local_input_fails_closed_without_overwrite`
- `test_stage5_overview.TestStage5OverviewRebuild.test_issue68_t68_7_legacy_program_pack_contributes_no_rows`

**P6 · AD68-3 · 4 项**（只读发现逐包独立；坏包不影响其他包，且发现结果不产生不支持的选择范围）：

- `test_issue68_choices_attribution.TestStage5ListInputs.test_issue68_r10_list_inputs_discovers_local_packs_independently`
- `test_issue68_choices_attribution.TestStage5ListInputs.test_issue68_r10_list_inputs_professor_filter_and_ambiguity`
- `test_issue68_choices_attribution.TestStage5ListInputs.test_issue68_r10_list_input_reason_codes`
- `test_issue68_choices_attribution.TestStage5ListInputs.test_issue68_r19_scope_emission_is_not_supported`

**P7 · R68-8、AD68-4、AD68-5 · 20 项**（根代理确定性分配、歧义拒绝、所有者归属，以及目录、邮件包、编号和选择原值保持）：

- `test_issue68_choices_attribution.TestStage5ChoicesAttribution.test_issue68_r10_counterexample3_unique_candidate_legacy_row_is_a_duplicate`
- `test_issue68_choices_attribution.TestStage5ChoicesAttribution.test_issue68_r10_counterexample4_multi_candidate_excludes_satisfied_owner`
- `test_issue68_choices_attribution.TestStage5ChoicesAttribution.test_issue68_r10_undecided_multi_candidate_owner_returns_needs_input`
- `test_issue68_choices_attribution.TestStage5ChoicesAttribution.test_issue68_r10_counterexample2_cross_professor_error_stays_with_its_owner`
- `test_issue68_choices_attribution.TestStage5ChoicesAttribution.test_issue68_r10_counterexample5_invalid_explicit_dir_never_transfers_by_id`
- `test_issue68_choices_attribution.TestStage5ChoicesAttribution.test_issue68_r10_foreign_rows_stay_noise_without_a_scope`
- `test_issue68_choices_attribution.TestStage5ChoicesAttribution.test_issue68_r10_single_object_choices_and_default_scope_keep_working`
- `test_issue68_choices_attribution.TestStage5ImmutableWrapperOwnerLocalChoices.test_issue68_r10_wrapper_attribution_matches_the_runner`
- `test_issue68_root_partition.TestStage5RootPartition.test_r12_cx1_malformed_b_pack_does_not_block_a_bundle`
- `test_issue68_root_partition.TestStage5RootPartition.test_r12_cx2_owner_bundles_hold_only_their_own_professor`
- `test_issue68_root_partition.TestStage5RootPartition.test_r12_cx3_colliding_legacy_row_is_ambiguous_at_root`
- `test_issue68_root_partition.TestStage5RootPartition.test_r12_cx3b_explicit_row_resolves_colliding_legacy_row`
- `test_issue68_root_partition.TestStage5RootPartition.test_r12_cx4_targeted_bundle_excludes_unselected_same_professor_rows`
- `test_issue68_root_partition.TestStage5RootPartition.test_r12_cx5_b_choice_error_does_not_degrade_a`
- `test_issue68_root_partition.TestStage5RootPartition.test_r12_cx7_discovery_rows_drive_partition_and_bad_b_stays_alone`
- `test_issue68_root_partition.TestStage5RootPartition.test_r12_owner_bundle_has_no_scope_and_no_sibling_state_paths`
- `test_issue68_root_partition.TestStage5RootPartition.test_r12_partition_preserves_rows_and_reruns_deterministically`
- `test_issue68_root_partition.TestStage5OwnerLocalBundleLoader.test_sibling_explicit_row_in_owner_bundle_fails_closed`
- `test_issue68_root_partition.TestStage5OwnerLocalBundleLoader.test_owner_local_legacy_exact_one_still_applies`
- `test_issue68_root_partition.TestStage5OwnerLocalBundleLoader.test_targeted_bundle_of_one_stays_exact`

这 43 个组件名称、proof 归属和数量是执行映射；它们不是 43 次独立正式用例。每个组件只由所属 proof 调用一次；三个 proof 层级的归属不可互换：P5 的确定性总览组件不证明 PC68-R1 的运行时总览顺序，P7 的选择分配不证明实际委派或教授读取，只有 PC68-R1 能证明这些真实运行事实。

**历史执行记录。** 此前在执行主机临时目录中读取过原始记录；该目录未随仓库移交。`execution-record.json` 将运行绑定到 case=`PC68-D1`、候选 `issue68-r29-r23-candidate-2026-10-06`、测试代码 `e931ab22fbe492bdf0c4ecb74e906d2c23dfce23`、干净产品 `35f2785b4d13783683860db910a36add2347bd29`；时间为 `2026-10-06T00:25:07+0800` 至 `2026-10-06T00:25:51+0800`，机器 verdict=`PASS`，退出码 `0`。7 个外层测试正常结束，0 跳过、0 预期失败、0 意外成功、0 失败、0 错误；P1—P7 的历史组件数分别为 4、4、2、2、7、4、20，共 43。此前读取的文件包括 `command.txt`、`execution-record.json`、`proof-counts.json`、`output/proofs.json`、`output/unittest.txt`、`output/final-verdict.json` 和 `runner-exit-code.txt`。历史命令未传 `--execution-kind`，故记录为 `preflight`；其 case 仍是正式 `PC68-D1`。这次旧产品/旧候选的结果不代表目标产品 `b39a4252e3ce473f8cdeedd2e12b0cf86d6f597d` 或当前测试实现候选已通过；此处只保留原结论，不判断复用或关口状态。

| 证明 | r25 保留的证明内容 | 本轮测试改动影响分析 | 历史执行结果（非当前候选结论） |
| --- | --- | --- | --- |
| P1 | `R68-1/R68-6`：显式本地邮件包是唯一事实来源；无缺失回退、旧全局包、双读、双写或第二次迁移 | 本轮观察修改位于 PC68-R1 的运行时证据解析、入口、契约、根提示和运行时单元测试；没有意图改变产品本地事实来源或 P1 确定性组件。 | 历史执行 P1 为 4/4；旧产品/候选结果，不是当前版本结论。 |
| P2 | `R68-2/R68-7`：指定邮件只处理目标、无关行不阻断，目标本身非法时拒绝；校验与状态记录限当前输出 | 当前改动没有改变目标邮件确定性用例或产品校验。本轮对真实教授输入的观察属于 R1，不能替代 P2 的目标过滤和失败断言。 | 历史执行 P2 为 4/4；旧产品/候选结果，不是当前版本结论。 |
| P3 | `R68-3`：不指定邮件时只处理本教授整包；合法时整批提交，非法时不部分提交且文件内容不变 | 当前改动没有改变同教授原子批处理组件或产品提交路径；R1 的首次计划早停不证明整批写入/回滚。 | 历史执行 P3 为 2/2；旧产品/候选结果，不是当前版本结论。 |
| P4 | `R68-4/R68-7/R68-8`：乙失败不阻断或回滚甲；验证和记录只基于当前教授输出 | R1 的实际输入观察加强真实数据归属证据，但不重跑或改写 P4 确定性交易、校验用例。若产品交易代码、校验语义或 P4 组件变化，只重开对应证明；本轮直接输入本身由 R1 覆盖。 | 历史执行 P4 为 2/2；旧产品/候选结果，不是当前版本结论。 |
| P5 | `R68-5`：总览从本地状态派生，不进教授提交门；人工修改保护。`AD68-2` 的通用写锁归第 48 号，本用例不设对应测试组件。 | P5 确定性证明与 R1 根总览顺序/真实输出来源是不同事实。当前解析观察不改变 P5；R1 必须独立保存根总览调用输出及最终报告。 | 历史执行 P5 为 7/7；旧产品/候选结果，不是当前版本结论。 |
| P6 | `AD68-3`：发现只读且逐包独立，坏包只影响自身，不读取全局包或其他业务状态 | 当前 R1 仍需记录正式根发现的直接输出；该输出不能替代 P6 确定性发现组件。运行观察解析未改变 P6 产品入口。 | 历史执行 P6 为 4/4；旧产品/候选结果，不是当前版本结论。 |
| P7 | `R68-8/AD68-4/AD68-5`：根代理确定性分配、归属与歧义处理、选择保留、路径和编号原值保持 | R1 新增的真实边界是将根分配结果连到教授实际解析对象；这不改变 P7 确定性组件，但 P7 的本地归属断言和 R1 的真实读取证据互补、不能互相替代。 | 历史执行 P7 为 20/20；旧产品/候选结果，不是当前版本结论。 |

历史运行证据与本节映射可逐项对应；此处只记录旧执行的原始结论，不将其扩展成当前版本结果，也不判断复用范围。

## 10. 完整复验依赖与重新开启条件

`PC68-R1` 对当前版本要求 `EXECUTE_CURRENT`，不能以旧运行代替。它依赖：产品及安装技能/代理说明；测试入口、观察信封与判定程序；根发现、根分配和教授交接；实际解析对象及同次 `argv`、计划输出；正式线程关系和逐教授结果消费；总览调用及最终报告；实际 `model`、`executor`、`entrypoint`、`isolation`、`shared assets`、`service version`；真实输入、路径、标识、原始选择和缺核验状态。主机、适配器、进程号和端口只可作诊断信息，不是独立必填项。观察程序、输入关联、入口或判定一旦变化，必须对受影响预检重新取得证据；正式 PC68-R1 在第二关口通过并指定唯一完整候选后执行一次。

`PC68-D1` 按组件依赖重开，不因提交编号变化自动全量重跑。产品本地包权威或迁移变化影响 P1；目标过滤和自身非法输入影响 P2；整包批处理/回滚影响 P3；教授交易、校验或状态记录影响 P4；总览派生和人工修改保护影响 P5；发现读取边界影响 P6；选择分配、归属、歧义或原值保持影响 P7。对本轮 PC68-R1 观察解析的改动，不以它替代任何 P1—P7；原始 P1—P7 证据核验结果再决定是否可复用。

每次正式尝试须保留完整 runner 记录、请求及响应、原始事件、正式线程图、读取观察信封、真实 `argv`、计划输出、分配与消费回执、总览输出、产品/消费者/fixture/服务版本、请求前后隔离证据、所有输入与输出文件状态及唯一结论。证据须足以在传递文件清理后再次核对实际读取内容与来源。禁止用二次运行替代本次输入观察；禁止清理原始正式尝试后再重建通过结果。

## 11. 当前关口结论及限制

- 测试计划 r25 是唯一当前依据，完整取代 r24；产品方向 r13 和产品目标 SHA 固定如第 1 节。
- 契约 JSON 格式检查通过；本轮实现提交 `f08474bfb73389488a462619ae9a0913fc8338b0` 对应的 20 项定向单元检查和本地合成采集预检通过：真实合成 CLI 返回 `status=ok`，runner 落盘并重读 stdout/manifest 后判为 `verified=true`、`reason=null`。这些结果只证明本地合成调用路径。
- 实际 `model`、`executor`、`entrypoint`、`isolation`、`shared assets`、`service version` 尚未采集；真实 `app_server` 事件和正式教授线程/调用归属也未核验。Gate 2 仍为 `INCOMPLETE`；runner 必须先返回 `CASE_NOT_STARTED`，不得触碰评估服务。评估服务、正式请求和 `PC68-R1` 均未运行。
- PC68-D1 历史记录曾在执行主机临时目录中可读，包含 43 个组件回执；该目录未随仓库移交。记录绑定旧产品与旧候选版本，只保留为历史 `PASS`，不能记成当前目标产品或当前候选通过。
- 本轮测试实现候选完整 SHA 为 `f08474bfb73389488a462619ae9a0913fc8338b0`；须经第二关口审核后才能冻结并用于正式运行。
- 第 3 节的六项运行事实、产品和共享资产实际检出以及 PC68-R1 真实输入值均未采集；不得猜测。主机、适配器、进程号和端口不是独立必填。Gate 2 审核通过且必填事实固定前，不启动正式请求；本次未运行评估服务或发送请求。
