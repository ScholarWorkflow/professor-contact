# 第72号拉取请求完整测试方案第37版

方案编号：`issue-68-test-plan-r37-2026-10-08`。本版依据第36版正式运行的无效执行和独立实现审查，授权在独立新运行编号下再发送一次正式 `PC68-R1` 请求。该请求不是对旧请求的重判或覆盖；旧请求及其 `INVALID_TEST_EXECUTION / NOT_DETERMINED` 结果完整保留。新请求必须使用包含已修订根调用说明的产品提交 `faab365d0be2bb66f2f285fdaa2927631dbf33f8`，并在独立计划审核及本版 Gate 2 `PASS + COMPLETE` 后才可启动。

本版不改变冻结验收第四版、第十三版产品计划、正式用例数量、业务输入预期或产品通过条件。它只收紧 `PC68-R1` 的根输入提取、发现路径保留、单次完整分配、教授结果回执、必做总览和清理执行步骤，并规定旧无效执行的处置及本次重开范围。正式运行严格按本版执行；新请求一经发送即停止任何完整请求重试。

本版是唯一测试方案正文，完整取代第36版；不新增旧计划副本。历史运行结果、原始证据及审核记录保留。本文收齐当前要求，执行者无需拼接旧计划。本版候选须经独立计划审核和完整 Gate 2 审核；作者的修订不算独立审批。

本次 Gate 2 重开记录：触发事实为第36版 Gate 2 后出现的有效运行证据及独立审查，确认根任务的实际 choices 内容错误、路径被改写后另行分配、总览漏调用、传递文件未清理；同时当前调用方说明从旧产品提交 `b39a4252e3ce473f8cdeedd2e12b0cf86d6f597d` 改为包含修订说明的 `faab365d0be2bb66f2f285fdaa2927631dbf33f8`。变化影响 `R68-8 / AD68-1 / AD68-4 / AD68-5` 的 `PC68-R1` 正式调用、输入、实际运行行为及生命周期证据；既有 `PC68-D1` 和未变的 R19 判定器及生命周期测试可复用原 PASS。旧 `PC68-R1` 无效，不能重判或复用。当前方案若继续使用旧产品提交或允许根任务在一次请求内追加分配，会再次检验未修订的调用说明或重复旧执行偏离；因此本版固定新产品提交、规范步骤和唯一新请求，`PC68-R1` 采用 `EXECUTE_CURRENT`。本版 Gate 2 仅重审上述受影响证明及直接依赖，并确认完整方案自洽。

修订原因：第31版将独占临时缓存写成当前执行前提，却未核实该选择与共识环境准备规则的对应关系。该审核遗漏记为 `REVIEW_DEFECT`；没有错误判定实例时，不追溯撤销原第31版结论。本轮用户明确要求评估时使用自动审批，这是新的运行配置输入，命中PC68-R1及评估预检的配置、提示词与权限依赖，按测试规则第6.2节限定重审这些范围。原移除 `formal_run_allowed` 布尔许可门槛的决定继续有效。

第32版自行选择逐请求审批覆盖，在议题及拉取请求重复配置，并冻结了独立权限说明、命令关联取证和接线细节。此次用户确认沿用共享环境项目配置入口；按项目共识“运行配置的唯一来源”及测试规则第2.1、3.2节修正。审批使用方式是运行前提；本例不负责证明审批系统自身正确，不增加审批专项证明或与业务验收无关的取证门槛。

第36版历史安装及预检状态（截至 R16；以下均为历史记录，不代表第37版准入结论）：第31版第二关口的历史 `PASS / COMPLETE` 保留其原提交 `8a8a2fa02288c463eefcc0d116fe306b35d664b3` 来源。第36版记录共享配置准备入口及其固定版本。R07 的支持安装因依赖传输中断而失败；R08 安装成功，但发现配置助手在安装后运行，与 APM 已创建配置文件冲突。修正顺序后，R09 在全新消费者中完成支持安装，安装前配置助手创建的两个审批值均被 APM 保留，评估服务响应也实际报告 `on-request` 与 `auto_review`。R09 唯一一次合成目录请求未能运行标记命令：响应中的 agentMessage 自述用户级 uv 缓存权限错误和退出码 2，但原始响应没有 commandExecution 事件，也没有对应 uv 标准错误输出，因此该原因未获机器事件证实。机器观察保持 `NOT TESTED / marker_command_not_observed`。R10 在全新消费者安装成功，32.1秒安装10个依赖和1个MCP服务；R11 在依赖解析处停滞710.7秒后被中断，退出130。R12 与 R13 分别因 `knowledge-tools` 和 `paper-analysis` 的 HTTPS/TLS 连接意外中断而失败，均未提交安装事务。R14 在全新消费者中于28.5秒安装成功，安装10个依赖和1个MCP服务，且安装后两个项目审批值保持不变。R15 于300秒超时退出124，未达到第4节规定的600秒保护窗口，按执行偏离登记；R16 在全新消费者中用49.5秒安装10个依赖和1个MCP服务，安装后两个项目审批值保持不变。R10–R16 均未发送评估请求。一次误从测试检出目录启动的安装和一次未能启动 APM 的包装器调用已排除在安装结果之外，详见证据中的 `excluded_invocations`。R09已发送的请求保持不重发；截至R16，正式 `PC68-R1` 尚未启动。后续安装重试与顺序探针见 `tests/runtime/evidence/issue68-r36-project-approval-config-preflight-continuation-20261008.json`。

第36版续试历史（仅记录 R17；不代表第37版准入）：R09仍保留原状态，未重发该请求。用户随后授权在R16安装成功后执行新的预检；R17按固定流程成功安装，并以一个新请求验证标记操作，机器结果为 `PASS`。启动器首次受默认缓存目录权限阻挡，未启动预检脚本、安装或请求；改用仅供本地启动器使用的临时缓存后，R17完成。截至R17，第二关口仍待独立审核，正式R1尚未启动；后续正式尝试状态见第10节。详见第4.1节、第10节及上述续试记录。

## 1. 权威来源与版本

| 项目 | 固定来源与版本 |
| --- | --- |
| 冻结验收 | `issue-68-gate1-r4-2026-10-05`，[第68号议题第四版](https://github.com/ScholarWorkflow/professor-contact/issues/68#issuecomment-5981562292)，决定人为 `RekiDunois` |
| 获批产品计划 | `issue-68-plan-r13-2026-10-06`，[第十三版](https://github.com/ScholarWorkflow/professor-contact/issues/68#issuecomment-6000673923)，[范围批准](https://github.com/ScholarWorkflow/professor-contact/pull/72#issuecomment-6008709709) |
| 当前完整测试方案 | 本文，`issue-68-test-plan-r37-2026-10-08`；仓库唯一正文为 `docs/issue68-test-plan.md`，[第72号拉取请求分支上的当前正文](https://github.com/ScholarWorkflow/professor-contact/blob/codex/issue-68-stage5-per-professor/.apm/skills/professor-contact/docs/issue68-test-plan.md)。评论 [#6030951188](https://github.com/ScholarWorkflow/professor-contact/pull/72#issuecomment-6030951188) 是历史第29版，不包含本版 |
| 本版目标产品 | `faab365d0be2bb66f2f285fdaa2927631dbf33f8`；包含第36版审核后修订的根调用说明 |
| 共享测试资产（本次固定实现） | `d160ecb403c0f9e9c153f4b8383302a4b67664ab` |
| 项目配置规范来源 | `c738fa2f8bcbb16cd99d741332d5f59b062b6357` 的 `docs/codex-opencode-smoke-wiring.md` 第7.7节 |
| 第31版历史测试实现来源（不含本版新增接线） | 配置提取预检器摘要 `665f69e82da803935f42c25ee42dfe1824fac592e419b05a0744e85845f161e7`、对应测试摘要 `479a8a74d5f8fce9b689844e04adbaae239eee79777a6135f7220764a5242778`；正式入口摘要 `755a932f95fcdb51ad6a93507aba8794330de03bab91107b9dd292b3158909ba`、对应测试摘要 `df4cfe300d3ad54fbe23330c0c71b3eca7d67d4931dd4aa379aa43321a1c658b`；证据合同摘要 `6c31a1fc408a12cee99dc823db0c62c7c699db568bc977a995e9b67e2a033acd`。56 项入口测试及 37 项配置与传递位置测试均通过 |
| 历史安装续试基线 | 当时候选 `806066a`；对应安装恢复证据保留，不作为当前测试实现版本 |
| 第36版原固定实现（历史来源） | 预检器 `preflight_issue68_transfer_location_eval_r33.py`：`bf816054899d33a7072d114c4331f3bb7cd2355b82318183ed4205ec23597c21`；正式入口 `run_issue68_stage5_routing_r19_codex.py`：`88896013563833ef8b839ec08fefc66635eb03a85107a1c30d615a54665d0b0d`；安装器 `run_issue68_stage5_routing.py`：`c232b5782f6505a886c7d68f19048820395400ec3e8aefe11c90b0df09f6e0a3`；预检单测 `test_issue68_transfer_location_eval_r33.py`：`0ddc09c7487f611ce29bda077074d8a03524f504f16adf64f7bcd92e1cdcb2e5`；目录接线回归单测 `test_issue68_transfer_location.py`：`18352858c1cabbfa39d70f9c50fbb2929969a980fea99a47816b23d23cd29335` |
| 第36版 Gate 2 修订候选源码清单 | 候选源码提交 `4c866becca95a14585332f506846d9e5b6a459e6`（测试时工作树以 `f62c8fd6792022c3cecfe915226fa501e0be2605` 为基线；提交后已核对文件摘要与下列清单一致）；判定器 `verify_issue68_stage5_routing_r19.py`：`57570db77ee4eb7cbf3619262e6707468705b8d9cc01b720b3e350362ec83384`；生命周期模块 `issue68_lifecycle.py`：`bdaa8a65f65835d587978061740fb17405a07631f146eb28abae3faa33a6fefd`；R19 单测 `test_issue68_runtime_r19.py`：`6eb400ac1535ecbef10c29e96064b2496a0fe29bd734fc40edb5eca0d09bb729`；生命周期单测 `test_issue68_lifecycle.py`：`f2f88e22497f1987e94fb7f0ecda57bb20791be57c0b9d502220098c5b7eb317`；生命周期组合单测 `test_issue68_lifecycle_integration.py`：`a32a366e8eaec90ab6c5887320308ebe2fd97c1ad3ace76f49c7fb4c382cc5f1`；运行证据约定 `issue68-runtime-evidence-contract-r19.json`：`b853ff0791078576d4464f026db003a232c487a1f6c770e229a417efcfc7a9a8`；正式入口 `run_issue68_stage5_routing_r19_codex.py`：`88896013563833ef8b839ec08fefc66635eb03a85107a1c30d615a54665d0b0d`；安装器 `run_issue68_stage5_routing.py`：`c232b5782f6505a886c7d68f19048820395400ec3e8aefe11c90b0df09f6e0a3`。本源码清单对应回归结果见 `tests/runtime/evidence/issue68-r36-gate2-fix-validation-20261008.json`；其测试针对以上 SHA-256 内容，旧正式尝试的 `test_revision=570b48ecfe4109016dcfd517a5a2f34fdea54b64` 不代表本候选源码清单 |
| 第36版 Gate 2 第二次修订候选源码清单 | 测试源码提交 `d35d42d5cc3b88014af8eff171f266f93d5051a7`，父提交为 `51822296c91a15683e3636f02d5ef5d50b1002e7`；更新后的 R19 单测 `test_issue68_runtime_r19.py`：`e0d92ba1091459f4879ad705bcc2dc67e681d6bf6283ad06cd05e5da719506d7`；生命周期单测 `test_issue68_lifecycle.py`：`6230d7bb529579b1f9bfc873966bfe0d91259096dfd5f9946b51b8b5d12d7b23`；生命周期组合单测 `test_issue68_lifecycle_integration.py`：`1b9808c15010230d560e0356a65be35552f875a2dacdf22ff9e6d983c3aa8b31`；其余五项沿用上一行未变源码。完整八项摘要、142 项复验命令与原始控制台摘要见 `tests/runtime/evidence/issue68-r36-gate2-prefix-matrix-validation-20261008.json`；对应当前计划摘要将在提交候选计划后写入该记录 |
| 根代理调用说明审查修订 | `SKILL.md` 修订前 SHA-256 `36af7474af8ed96930de8091263ee8e17c5162dc506a76c4ed177bf45f8c599d`；修订后 SHA-256 `555839c6eebe667a1519bc636db0e044c8d4779111f6527f3b5ced6b91584626`。修订明确只保存 `choices` 列表、逐字沿用已发现路径、一次提交全部 owner，并在消费全部结果后必须重建一次总览；它不属于前述 142 项自动测试输入。独立执行审查见 `tests/runtime/evidence/issue68-r36-implementation-execution-audit-20261008.json` |
| 第36版运行证据约定 | `tests/runtime/issue68-runtime-evidence-contract-r19.json`，修订 `issue-68-runtime-evidence-r34-2026-10-08`，SHA-256 `b853ff0791078576d4464f026db003a232c487a1f6c770e229a417efcfc7a9a8`；作为历史版本保留 |
| 规则来源 | 本次修订已读取工作区有效的 `PROJECT_CONSENSUS.md` 与 `Test Engineer Rule.md`；当前文件摘要分别为 `2aebd20d61e111722e4ec39f2666ba240dc97c9efd15d4f81824b584abad72b1`、`b76bb0d3553f9bd42e4ae2efb7dc98acf6c593d36e3c003a955d3db3c0fbdb46`。审批接线引用第3.1节共享环境来源，本轮用户确认沿用其项目配置入口 |
| 第37版候选实现与验证 | 历史记录 `tests/runtime/evidence/issue68-r37-gate2-validation-20261008.json` 保留预检修正前216项通过的结果；历史记录 `tests/runtime/evidence/issue68-r37-gate2-validation-20261008-02.json` 保留219项通过；历史记录 `tests/runtime/evidence/issue68-r37-gate2-validation-20261008-03.json` 记录上一候选221项通过。当前候选验证及完整源码摘要记录于 `tests/runtime/evidence/issue68-r37-gate2-validation-20261008-05.json`，其计划摘要必须等于本版本文摘要；以上自动验证记录均不替代独立第二关口结论 |
| 第37版新鲜环境与传递目录预检 | 脱敏结果见 `tests/runtime/evidence/issue68-r37-preflight-validation-20261008.json`；保留每次失败及通过摘要和本地原始证据摘要。环境预检第03次为 `PRECHECK_READY`，目录预检第02次为标记操作 `PASS`；二者都未启动正式 `PC68-R1`，也不代表 Gate 2 通过 |

本文所有仓库内路径以 `.apm/skills/professor-contact/` 为前缀。第36版独立实现审查发现根代理保存了外层业务对象、改写发现路径后另行分配、漏掉总览调用并未清理传递文件。第36版后已修订 `SKILL.md`；本版再把正确选择列表、发现路径及单次完整分配明确纳入 R1 的输入与判定，并在新产品提交上按正式入口重新执行。未发现确定性业务代码缺陷；本版不重开验收和第十三版产品计划。独立工作树为当前第72号拉取请求的测试工作树，执行前在仓库根运行 `pwd`，用返回值设置 `PC68_TEST_ROOT`；公共记录仅使用变量，真实值留本地原始证据。独占传递目录由测试人员按第4.1节选择、预检并记录绝对路径；运行器会核实其为空目录、加入实际请求声明与来源记录，并将同一目录纳入请求前后观察。

本版保留固定输入、产品范围和六种整例终态；位置声明必须进入实际请求，根代理将位置转告负责者，同一目录须具有正式入口最小操作证据和完整前后观察。历史尝试只用于确认已有证据的证明范围；当前执行步骤全部在本文，不从旧计划补充或选择替代命令。

## 2. 用例与证明负责者

范围仅为第五阶段本地来源、指定邮件、同教授整批、逐教授隔离、选择分配与原值保持、只读发现、真实委派与结果消费、独立总览及临时传递清理。教授姓名假定唯一，同名支持、拒绝及测试均不在范围内。姓名不同但邮件编号相同的选择归属歧义仍在范围内。第67号负责上游交付与迁移，第59号单邮件兼容保持，第48号通用写锁不成为本任务新增前置。前四阶段、文案、联系方式判断与业务校验不新增要求。


正式用例只有 `PC68-D1` 和 `PC68-R1`。姓名假定唯一，同名支持及测试不在范围内。第五阶段本地来源、指定邮件、同教授整批、教授隔离、只读发现、分配与原值保持由下表负责；不增加前四阶段、历史迁移、写锁、文案与业务校验要求。

| 要求 | 负责证明 | 必须直接证明的事实 |
| --- | --- | --- |
| R68-1、R68-6 | PC68-D1/P1 | 显式本地邮件包唯一来源；缺包不回退，无全局双读写或第二迁移 |
| R68-2、R68-7 | PC68-D1/P2 | 指定邮件只处理目标；无关行不阻断，目标自身缺失、重复、身份、字段、收件人及日期错误仍拒绝；校验仅处理本教授输出 |
| R68-3 | PC68-D1/P3 | 同教授全部邮件整笔提交；全部合法才成功，失败无部分写入 |
| R68-4、R68-7、R68-8 | PC68-D1/P4；PC68-R1 | P4证明乙失败不回滚甲及本地校验隔离；R1证明真实逐教授委派与独立结果消费 |
| R68-5、AD68-2 | PC68-D1/P5 | 总览独立派生、人工修改保护、失败不反向改变教授结果；通用写锁归第48号实现职责 |
| AD68-3 | PC68-D1/P6 | 发现只读、坏包只影响自身，不用全局包或核验、状态、渲染、总览作为事实源，不输出跨教授选择范围 |
| R68-8、AD68-4、AD68-5 | PC68-D1/P7；PC68-R1 | P7证明确定性归属、过滤、歧义拒绝、本教授选择读取与包装原样转交；R1证明实际分配、教授读取、首次业务输入和临时清理 |
| AD68-1 | PC68-R1 | 根代理分别委派、等待并消费，随后必须恰好调用一次总览并单独报告真实结果 |

每个组件由所属证明执行一次，不因多个要求引用而重复。确定性组件不能替代真实委派、实际读取或根结果消费；真实运行不能宣称证明未发生的渲染、提交及后续选择读取。


R1固定为缺核验前提。已经发生的分配、读取、首次计划、结果消费及总览须直接证明；不得要求或宣称尚未发生的后续选择读取、渲染、提交和校验。后续选择读取由D1/P7承担。

## 3. 完整输入、允许变量和实现文件

输入由固定 `tests/runtime/prepare_issue68_stage5_routing.py` 的 `EXPECTED_OWNERS` 和 `test_contact_state.write_issue59_stage5_fixture` 生成，不由执行者猜内容，不从根分配输出反推预期。两位教授为 `試験 教授`、`佐藤 花子`，编号分别为 `試験 教授::DIR00001::DIR00001_1`、`佐藤 花子::DIR00001::DIR00001_1`；每份独立选择保留 `first_choice=false`、`signature_name=試験 太郎`、`learning=比較手法の基礎知識の習得`，以及各自 `transport_sentinel=owner-0/owner-1`。完整原始选择另有 `email_id=unselected::D::I`、`transport_sentinel=noise` 的无关行。坏包由 `ISSUE59_MALFORMED_JSON` 写入 `教授研究/Z分野/无效样例`。两位教授证据为 `none`、核验为 `missing`；模板、原始结果、包及状态由固定准备程序写出。

准备程序只检查本例核验前提并生成独立预期，不生成根代理交接或分教授选择包，不替根代理分配。其 `fixture-manifest.json` 归档教授目录、包、编号、全部选择、首次计划业务数据、预期结果、坏包路径及执行前文件摘要；`canonical-choices.json` 保存完整原始输入，`root-prompt.txt` 保存业务提示词。每位教授的首次计划调用预期为 `status=ok` 且该教授的 `verify=needs_recheck:missing`；独立预期结果明确为 `status=needs_refresh / reason_code=verify_missing`。这是两个不同的观察：前者是本次捕获的原始命令回执，后者是教授任务最终必须返回并由根任务原样消费的本用例测试专用预期。该固定终态由本任务用户明确指定，用户指出此前“没有形成本用例预期的 `needs_refresh / verify_missing` 结果”；它只约束此固定夹具要求教授子任务返回的对象，不表示产品首次计划命令回执为此结果，也不改写 `SKILL.md` §5.9 对一般 `needs_recheck` / `verify_missing` 的规则。准备程序可用带 `--result` 的本地输出检查该固定结果，但必须同时核对状态、原因码和退出码，并且只把固定的 `needs_refresh / verify_missing` 投影写入清单；不能把产品回执本身当成预期来源。判定器也拒绝任何不同的清单预期。不得把首次计划回执直接当作教授最终结果。位置绑定帮助分别保存 `codex/business-prompt.txt` 和 `codex/transfer-location-declaration.txt`，再将声明与业务提示合并交给固定请求构造器；绑定记录保存目录、声明与业务提示摘要及实际请求摘要。输入字节与初始状态以该固定程序及本次归档为唯一来源。

`PC68_PRODUCT_ROOT` 为干净产品检出目录，`PC68_SHARED_ROOT` 为固定共享资产的干净检出目录，`PC68_EVAL_ROOT` 为现有评估服务检出目录；先在各目录执行 `pwd` 取得绝对路径，保留到本次本地原始执行记录，再赋值，不在公共证据中泄露用户路径。`PC68_OUTPUT_ROOT` 为新建正式运行编号对应的空目录；`PC68_PREFLIGHT_ROOT` 和 `PC68_LOCATION_PREFLIGHT_ROOT` 是互不重叠、未创建的新合成预检输出目录，不使用已存在的第01或第02目录覆盖旧证据。

允许变量只有：产品检出绝对路径、共享检出绝对路径、评估服务检出绝对路径、全新且不相交的输出目录与运行编号、按第4.1节取得预检证据且初始为空的独占传递目录。这些由操作系统实际目录与服务 `direnv` 得到，执行前归档原值。产品与共享提交、输入内容、业务提示词、模型、执行器、观察程序、沙箱、入口和判定不得临场替换。位置声明与业务任务分开保存，但必须进入实际请求及其来源证据；产品自行决定实际文件名和布局。默认模型及推理设置引用当前项目共识，并由固定请求构造器落实，保存请求值及服务公开的实际生效配置；有效模型尚未公开时如实标注，不将请求值称为已观测的有效模型；端口由既有服务读取，不自行分配或启停服务。

### 3.1 评估请求的自动审批与权限处理

本例使用自动审批，并沿用共享环境的项目配置入口。配置规范来源为共享资产提交 `c738fa2f8bcbb16cd99d741332d5f59b062b6357` 的[接线文档](https://github.com/RekiDunois/skills-test-fixtures/blob/c738fa2f8bcbb16cd99d741332d5f59b062b6357/docs/codex-opencode-smoke-wiring.md)第7.7节；只引用其中的项目配置入口、信任前提及生效值证据约定。评估入口和字段映射继续引用服务提交 `3fdfa9387140cfc2e2aa3af415f85015f79706d2` 的 `README.md` 与 `docs/appserver-migration.md`。本方案、议题和拉取请求不重复定义审批参数，也不以命令行覆盖代替共享项目配置。默认模型与推理设置继续以项目共识为准。

共享资产提交 `d160ecb403c0f9e9c153f4b8383302a4b67664ab` 新增 `scripts/prepare_codex_project_config.py`，文件摘要为 `4bd798a8c29ae93e1c65a261d85b21302422a4a7b0089ec6c62a974d5b6f9032`。该入口只从固定规范提交 `c738fa2f8bcbb16cd99d741332d5f59b062b6357` 的文档对象读取第7.7节，核对文档摘要后，在全新消费者中独占创建 `.codex/config.toml` 并回读核验；已有文件时停止，不改调用者主目录。此次将共享依赖固定到新增实现提交，规范内容仍绑定原文档提交；没有增加配置协议或审批系统探针，正式入口回归测试核对运行前提所要求的响应字段。

本地测试工程师按这些来源编写实际步骤，保存共享环境来源、项目配置及实际生效配置证据。配置文件存在不等于已经生效；必要命令因沙箱权限受阻时，由实际运行代理按受支持方式申请升级，交自动审批处理。目录预检的单次合成命令用 `uv --cache-dir` 指向本次运行目录中、位于 `transfer/` 目录旁的 `.uv-cache/`，避免写入不可用的用户缓存；该缓存不在消费者或受观察传递目录内，也不预热或更换网络依赖缓存。

第36版正式尝试已直接观察到根代理默认 `uv` 缓存不可写。为避免在新正式请求中临时改动环境，本版固定将 `PC68_UV_CACHE_ROOT` 设为本次 `PC68_OUTPUT_ROOT/uv-cache`，由运行器在准备输出根后创建并验证其可写、空且独占；请求 `manifest.uv_cache_dir` 和根提示中的占位符必须绑定同一绝对路径。由于正式请求经 HTTP `/eval` 发出，本地运行器的进程环境不会传入根线程；正式根代理和教授代理的每条 `uv run` 命令都须以 `UV_CACHE_DIR='<manifest.uv_cache_dir>'` 作为环境赋值前缀。验证器按 manifest 精确核对实际 `commandExecution.command`，教授捕获信封还须证明继承到同一路径。缓存目录不得位于受观察传递目录、消费者或源码目录内；请求完成并留存核验记录后只清理本请求缓存。不得使用默认用户缓存、预热或清除共享缓存。`UV_CACHE_DIR` 是 `uv --cache-dir` 的官方等价环境变量。

共享资产第7.7节同时包含审批专项用例；其固定探针、必须观察到审批、审批路由和跨命令升级关联证明不属于PC68-R1。本例只证明教授业务，审批是运行前提；正常缓存使审批没有发生时不增加阻断。保留运行原件及自然发生的受阻事实，不为证明自动审批另跑业务、追加探针或增加业务通过条件。拒绝或不可用阻止必要步骤时，按本文既有启动边界和六类终态处理；不能判为产品违约。

干净消费者仍由固定产品提交经支持安装路径生成，不手工修改其代理、技能、包装器或配置。固定共享实现提交新增的准备脚本用于创建项目配置；本地入口在正式干净安装及同一目录预检中调用它，并保存脚本摘要、规范来源、配置字节摘要与实际响应字段。目标配置文件存在不等于已经生效，只有服务响应实际公开的 `output.thread_start_effective.approvalPolicy` 和 `approvalsReviewer` 可证明该值。正式运行入口须保存这两个响应值及其原始响应摘要；只有两项均匹配时业务 `PASS` 才能保留。字段未公开时将其记为 `BLOCKED_OBSERVABILITY`，值不匹配时记为 `BLOCKED_DEPENDENCY`，响应值格式错误时记为 `INVALID_EVIDENCE`；已有直接成立的产品失败仍保留 `FAIL_PRODUCT` 并附上配置证据。本次共享依赖变更只为准备脚本增加新固定提交；产品提交、业务断言、评估服务和请求中的信任配置保持原值。

预检只补上述运行前提尚缺的最小依据，优先引用有效文档、合同和既有证据；确需实际请求时纳入已有目录预检，不新增请求次数或审批关口。未变安装、观察和判定证明保留原来源；本次不要求改写全部测试程序、生命周期子进程或业务证据合同。本文后续命令供测试工程师落实执行步骤时核对，不能用第31版程序声称新接线已完成。

| 文件 | 职责 |
| --- | --- |
| `tests/runtime/preflight_issue68_environment_r30.py` | 关口前支持安装、只读服务隔离、单次纯合成评估请求；没有教授业务、分配和委派 |
| `tests/runtime/preflight_issue68_synthetic_observation_r30.py` | 仅空白消费者单次合成普通命令观察；独立安装成功不等于本项完整环境预检已经通过 |
| `tests/runtime/preflight_issue68_lifecycle_observation_r30.py` | 历史第04次有限命令能力检查，保留原始来源，不能独自承担生命周期组合与传递位置验证 |
| `tests/runtime/test_preflight_issue68_environment_r30.py` | 环境预检解析的合法及反例验证 |
| `tests/runtime/capture_issue68_owner_stage5_plan_r1.py` | 正常交接单次解析，只读复制同一个对象，调用原已安装计划程序，保存实际参数与原始输出 |
| `tests/runtime/verify_issue68_stage5_routing_r19.py` | 完整分配包/目标/选择→真实解析对象→实际首次调用及业务数据核对 |
| `tests/runtime/run_issue68_stage5_routing_r19_codex.py` | 正式单次评估入口、版本/隔离检查、运行证据和判定 |
| `tests/runtime/issue68_lifecycle.py` | 请求前记录、真实使用、后记录与保护数据组合判定；额外观察根按清单读取。没有独立业务入口 |
| `tests/test_issue68_lifecycle.py` | 生命周期完整合法链、产品违约、缺失及归属损坏的合成验证 |
| `tests/test_issue68_lifecycle_integration.py` | 请求边界及原始证据重建、组成入口验证；完整合成教授事件通过原主判定及原输入解析，未替换解析或判定；结果见组合验证证据 |
| `tests/runtime/preflight_issue68_lifecycle_combination_r31.py` | 六种历史合成场景的本地真实子进程与完整目录记录；线程与运行事件为明确标注的合成材料，不发评估请求、不运行教授业务 |
| `tests/runtime/preflight_issue68_transfer_location_eval_r33.py`、`tests/test_issue68_transfer_location_eval_r33.py` | 正式评估入口的无业务目录操作、事件分类、隔离及目录前后判定；不执行正式教授用例 |
| `tests/runtime/preflight_issue68_transfer_location_r32.py` | 本版传递位置实际请求、同根完整前后观察与判定的本地合成预检；不调用评估服务、不运行正式教授业务 |
| `tests/runtime/issue68_transfer_location.py`、`tests/test_issue68_transfer_location.py` | 检查独占绝对目录、声明单独留档与实际请求摘要、业务/消费者路径隔离及传递目录观察绑定；不调用评估服务 |
| `tests/runtime/run_issue68_stage5_routing_r19.py` | 原流程接线，使用固定共享资产 |
| `tests/runtime/prompts/issue68-stage5-root.txt` | 只保留业务任务及只读观察安排，不教学分配结果或教授工作步骤；位置声明单独保存并绑定到同一实际请求 |
| `tests/test_issue68_runtime_r19.py` | 独立已知输入的判定正例、产品失败和无效/阻断反例；正式响应有效审批配置门控 |

## 4. 关口前最小预检与命令

先核对本文已列出的有效证据及源码、服务、配置、隔离条件和所选目录。未受影响的已完成检查直接复用。第3.1节要求共享项目审批配置，旧环境及目录请求未证明该前提；只补其实际接线及生效的最小依据，确需实际观察时纳入已有目录预检。其他未变检查不重复发请求。第4.1节的目录对应检查每次正式启动前必做。

按本版测试计划，在第二关口完整通过前完成正式入口可执行、隔离、可归属观察和判定正反例验证，并完成独占传递位置的请求与观察绑定检查，以及第4.1节同一正式入口的实际创建、读取、清理及生效审批配置预检。预检不运行完整教授业务，不委派教授，不产生正式验收结论；不恢复机器布尔许可门槛。

执行前分别进入产品检出、共享检出、评估服务检出和测试工作树，运行 `pwd`，直接将返回路径设置为 `PC68_PRODUCT_ROOT`、`PC68_SHARED_ROOT`、`PC68_EVAL_ROOT`、`PC68_TEST_ROOT`，归档本地原值。进入测试工作树的 `tests/runtime` 后运行 `pwd` 设置 `PC68_RUNTIME_ROOT`，再回到仓库根。用未存在的新运行目录设置 `PC68_PREFLIGHT_ROOT`；目录不与任一源码、消费者、旧预检或正式输出相交。正式输出 `PC68_OUTPUT_ROOT` 使用另一尚不存在的目录。将 `PC68_LOCAL_UV_CACHE_ROOT` 设为本机本次可写的独占缓存目录，只供本机启动 `uv run`；不得把本机环境变量当作跨 HTTP 传给评估线程的证据。`PC68_UV_CACHE_ROOT` 固定为 `PC68_OUTPUT_ROOT/uv-cache`，由运行器准备输出根后创建，只用于本次正式评估请求；它必须为空、可写且不与任何源码、消费者、评估服务、输入及传递位置相交。请求清单与提示词绑定同一绝对路径。`PC68_TRANSFER_ROOT` 是按第4.1节选定并取得实际预检证据的绝对空目录，不能是符号链接，也不能和产品、共享、服务、消费者、输入、输出或任一缓存位置相交；真实路径只写本地原始证据，公共文件使用变量名。

```sh
PC68_LOCAL_UV_CACHE_ROOT="$(mktemp -d /private/tmp/pc68-r37-local-uv-cache-XXXXXX)"
test -d "$PC68_LOCAL_UV_CACHE_ROOT" && test -w "$PC68_LOCAL_UV_CACHE_ROOT"
UV_CACHE_DIR="$PC68_LOCAL_UV_CACHE_ROOT" uv run --no-project python .apm/skills/professor-contact/tests/runtime/preflight_issue68_environment_r30.py \
  --producer-root "$PC68_PRODUCT_ROOT" \
  --fixture-root "$PC68_SHARED_ROOT" \
  --eval-direnv-root "$PC68_EVAL_ROOT" \
  --output-dir "$PC68_PREFLIGHT_ROOT"
```

该入口核对固定产品 `faab365d0be2bb66f2f285fdaa2927631dbf33f8`、共享资产及服务干净版本、隔离，然后按 `apm install https://github.com/ScholarWorkflow/professor-contact.git#faab365d0be2bb66f2f285fdaa2927631dbf33f8 --target codex --trust-transitive-mcp` 在隔离消费者支持安装，取得安装程序摘要和帮助退出码。安装保护窗口为600秒；失败或超时保留终态，不默默重跑。用户授权续试，或新的恢复事实或有区分作用的最小诊断成立时，按原支持路径新建消费者目录继续原来未完成的检查，不改产品、依赖引用或服务。成功安装后只发一次纯合成普通命令请求，复制一次真实解析对象，并由同一对象启动回显子进程；不读取教授包、不分配、不委派、不启停服务。

保存 `preflight-result.json`、`service.before/after.json`、`tool-versions.json`、`install/command.json`、安装及帮助日志、`synthetic-manifest.json`、合成输入和脚本、`prompt.txt`、`request.json`、`response.json`、`observation.json`、`integrity.json`。以解析后的状态、原因、退出码和来源摘要判断，不能从日志出现某个词推断成功。`PRECHECK_READY` 只表示此入口的必要检查就绪，不是第二关口批准。字段缺失、对象结构损坏及实际来源矛盾分别按固定判定分类。

| 必要预检 | 需要回答的事实 |
| --- | --- |
| 正式入口可执行 | 固定产品支持安装成功，实际安装入口摘要、帮助退出码及固定共享请求构造器可用 |
| 环境隔离 | 独占消费者、输入及输出；服务进程、测试存储、工具和配置的只读前后证据可归属；不连接用户数据 |
| 必需观察可取得 | 普通命令的真实输出能保存单次解析对象，关联同一运行代次、线程、轮次、调用和顺序；正式委派及结果消费沿用固定共享适配器的原有约定 |
| 判定能区别结果 | 正常链可认可；有效产品违规不能通过；缺失或损坏不能误判通过；独立已证违规不能被其他缺证遮蔽 |
| 生命周期组合 | 同一合成隔离请求前完整记录、程序化形成、一次实际读取、请求及读取者结束后的完整后记录、保护数据不变，组合可认可；不限定写删命令形式 |

生命周期最小非验收检查使用下面的固定入口。`PC68_COMBINATION_ROOT` 是尚不存在的独占临时目录，不能覆盖旧材料。入口不强制依赖旧第03、04次临时原件；可选 `--historical-response-03`、`--historical-response-04` 参数只复查原字段约定。默认入口可独立执行，不发评估请求，不运行教授业务。

```sh
UV_CACHE_DIR="$PC68_LOCAL_UV_CACHE_ROOT" uv run --no-project python .apm/skills/professor-contact/tests/runtime/preflight_issue68_lifecycle_combination_r31.py "$PC68_COMBINATION_ROOT"
jq '{state, formal_case_started, cases, uncompleted}' "$PC68_COMBINATION_ROOT/summary.json"
```

传递位置请求与观察的本地合成预检使用新的空输出目录 `PC68_LOCATION_PREFLIGHT_ROOT`，调用实际请求构造器与生命周期观察器；只运行本地文件操作，不发送评估请求。每个场景保存实际请求、清单、请求前快照、合成实际读取、响应、请求后快照、生命周期证据及机器判定；汇总记录保存场景预期、终态、源码摘要和运行边界，命令与退出码另记入配套证据。成功场景须证明选定位置的请求前后完整快照相同且为空。七个场景均符合固定预期且命令退出0时，才记 `TRANSFER_LOCATION_PREFLIGHT_READY`。

```sh
UV_CACHE_DIR="$PC68_LOCAL_UV_CACHE_ROOT" uv run --no-project python .apm/skills/professor-contact/tests/runtime/preflight_issue68_transfer_location_r32.py "$PC68_LOCATION_PREFLIGHT_ROOT"
jq '{state, formal_PC68_R1_started, eval_service_called, cases, source_sha256}' "$PC68_LOCATION_PREFLIGHT_ROOT/summary.json"
```

每个场景保存 `request.json`、`before.json`、`actual-use.json`、`response.json`、`manifest.json`、`lifecycle-evidence.json`、`after.json`、`result.json`，总记录为 `summary.json`。本轮七种场景为：成功形成、读取并清理；传递文件残留；既有保护数据变化；错请求；漏扫；缺少实际使用；传递位置超出观察范围。成功链的文件形成、读取、清理及完整目录记录来自本地实际文件操作；线程、轮次、运行代次和事件信封是合成材料。该预检证明新增位置接线与合成判定可区分七种场景，不证明正式评估线程归属、根代理实际转交或教授业务结果。第03、04次原始记录仅保留其真实能力来源。

固定程序验证入口如下；每个新检查的完整输出使用独有文件保留，记录该轮版本、命令、退出码及耗时，不把多轮项数累加。样例预期由本版设计和独立已知输入确定，不由当前判定器反推。

```sh
UV_CACHE_DIR="$PC68_LOCAL_UV_CACHE_ROOT" uv run --no-project python -m unittest discover -s .apm/skills/professor-contact/tests -p test_issue68_runtime_r19.py
UV_CACHE_DIR="$PC68_LOCAL_UV_CACHE_ROOT" uv run --no-project python -m unittest discover -s .apm/skills/professor-contact/tests -p 'test_issue68_lifecycle*.py'
UV_CACHE_DIR="$PC68_LOCAL_UV_CACHE_ROOT" uv run --no-project python -m unittest discover -s .apm/skills/professor-contact/tests -p test_issue68_runtime_recipe.py
UV_CACHE_DIR="$PC68_LOCAL_UV_CACHE_ROOT" uv run --no-project python -m unittest discover -s .apm/skills/professor-contact/tests -p test_issue68_uv_cache_r37.py
UV_CACHE_DIR="$PC68_LOCAL_UV_CACHE_ROOT" uv run --no-project python -m unittest discover -s .apm/skills/professor-contact/tests/runtime -p test_preflight_issue68_environment_r30.py
UV_CACHE_DIR="$PC68_LOCAL_UV_CACHE_ROOT" uv run --no-project python -m unittest discover -s .apm/skills/professor-contact/tests -p test_issue68_transfer_location.py
UV_CACHE_DIR="$PC68_LOCAL_UV_CACHE_ROOT" uv run --no-project python -m unittest discover -s .apm/skills/professor-contact/tests -p test_issue68_transfer_location_eval_r33.py
jq -e . .apm/skills/professor-contact/tests/runtime/issue68-runtime-evidence-contract-r19.json
```

当前组合验证至少包括：程序化形成、真实使用、最终清理且保护数据不变；有效证据下传递文件残留；保护数据被删除或改动；前后记录错请求；缺中间使用；观察漏扫；合法成功没有特定写入或删除事件仍能认可。已形成但未交付文件不能被省略。实际包、目录、目标及完整选择改写、首次业务错包/错编号/兄弟任务仍判产品失败；正确对象只在命令文字、打印预期、无关读取或事后读取出现不能建立证明。缺核验早停认可已发生读取及任务生成，不增加后续业务义务。真实采集缺失、截断或错配按实际终态分类；第26版已撤回手工制造重复开始及配对命令不一致两份样例的独立必修要求，不为此增加请求或产品条件，原程序与所有历史尝试仍保留。

### 实际预检与历史来源

| 尝试 | 已有结果及保留来源 | 对当前证明的意义 |
| --- | --- | --- |
| 第30版第01次 | 支持安装240秒超时，退出124；`tests/runtime/evidence/issue68-r30-environment-preflight-01.json` | 环境未完成，不判产品或测试设计失败 |
| 第30版第02次 | 原支持安装600秒超时，退出124；`tests/runtime/evidence/issue68-r30-environment-preflight-02.json` | 安装摘要及帮助未完成；没有发送合成请求，不覆盖第01次 |
| 第30版第03次 | `SYNTHETIC_OBSERVATION_READY`、退出0；`tests/runtime/evidence/issue68-r30-synthetic-observation-03.json` | 单次解析、同对象转交和命令关联可复用；不证明安装或教授业务 |
| 第30版第04次 | `SYNTHETIC_LIFECYCLE_READY`、退出0；`tests/runtime/evidence/issue68-r30-lifecycle-observation-04.json` | 仅三条有限命令的真实观察及前后保护材料；不证明本版组合实现完成 |
| 第31版完整环境预检第01次 | `tests/runtime/evidence/issue68-r31-environment-precheck.json`：600秒保护超时124，预检退出1，`PREFLIGHT_INCOMPLETE/supported_install_failed`；先前最小远程诊断退出0，未证明安装恢复 | 产品与共享资产干净，服务前后不变；未进入安装入口帮助或合成请求；该历史超时不判产品失败 |
| 第31版安装重试第01次 | `tests/runtime/evidence/issue68-r31-install-retry-20261007.json`：1.290秒退出1，证书验证拒绝 | 未完整安装；未检查入口帮助、未发评估请求 |
| 第31版安装重试第02次 | `tests/runtime/evidence/issue68-r31-install-trust-retry-20261007.json`：24.124秒退出1；系统证书配置后仍有两个依赖的加密连接意外中断 | 仅进程证书配置；安装事务未提交，保留失败依赖与诊断 |
| 第31版安装重试第03次 | `tests/runtime/evidence/issue68-r31-install-recovered-retry-20261007.json`：34.166秒退出1；两个依赖远程引用查询成功，安装仍因 `knowledge-tools` 加密连接意外中断失败 | 查询成功仅支持新尝试，不代表安装成功 |
| 第31版安装重试第04次 | `tests/runtime/evidence/issue68-r31-install-http1-retry-20261007.json`：24.467秒退出1；此前以 `HTTP/1.1` 完整浅克隆成功，原安装仍因 `knowledge-tools` 加密连接意外中断失败 | 诊断检出未用于安装；未改变产品或依赖引用 |
| 第31版安装重试第05次 | `tests/runtime/evidence/issue68-r31-install-only-retry-success-20261007.json`：38.838秒退出0；锁文件解析到固定产品提交，安装入口摘要与产品源一致 | 独立消费者中的支持安装成功；本次只安装，未运行入口帮助或合成评估，因此不代表完整环境预检通过。独立限定复核见 `tests/runtime/evidence/issue68-r31-install-only-retry-review-20261007.md` |
| 第31版完整环境预检第02次 | `tests/runtime/evidence/issue68-r31-environment-preflight-retry-20261007.json`：支持安装600秒超时，退出124；预检退出1，`PREFLIGHT_INCOMPLETE` | 停在 `base-skills` 依赖解析；未运行入口帮助或合成观察。该超时不判产品失败 |
| 第31版完整环境预检第03次 | 同上：安装27.3秒退出0，入口帮助退出0，预检退出0，`PRECHECK_READY`；一次合成命令观察为 `OBSERVATION_VERIFIED` | 固定产品安装摘要匹配；合成对象解析后原样转交。服务进程及版本、安装消费者和输入均前后不变。第二关口仍为 `INCOMPLETE`，正式许可关闭 |
| 第31版组合代码及验证 | `tests/runtime/evidence/issue68-r31-lifecycle-combination-validation.json` 保存61项组合、56项输入判定、11项执行步骤验证的独立命令、退出0及原日志来源 | 合成验证；不同轮次数量不相加，不代替正式验收或安装预检 |
| 第31版组合最小预检 | `tests/runtime/evidence/issue68-r31-lifecycle-combination-precheck.json` 保存六场景预期及实际终态 | 正常链认可、残留与保护变化拒绝、错请求/缺实际使用/漏扫不通过；实际本地动作与合成线程事件的区别如上所述 |
| 第32版传递位置预检 | `tests/runtime/evidence/issue68-r32-transfer-location-preflight.json` 保存七场景终态、命令退出码、测试结果及源码摘要 | 七种预期终态全部符合；成功场景在同一传递目录请求前后均为空。文件操作为本地合成实操，运行、线程和代理事件为合成记录；未调用评估服务，未启动正式PC68-R1 |
| 第37版环境预检第01次 | `tests/runtime/evidence/issue68-r37-preflight-validation-20261008.json`，原始证据别名 `$PC68_R37_ENV01_RAW` | 旧预检器固定共享版本为 `c738fa2f8bcbb16cd99d741332d5f59b062b6357`，而本次输入为 `d160ecb403c0f9e9c153f4b8383302a4b67664ab`；产品正确，检查在安装和请求前停止。修正预检器后保留本次失败 |
| 第37版环境预检第02次 | 同上，原始证据别名 `$PC68_R37_ENV02_RAW` | 产品、共享资产和服务版本均正确且干净；支持安装因 TLS 证书校验失败退出1，未提交安装、未发送请求。证书配置重试仅作用于新进程，TLS 校验保持开启 |
| 第37版环境预检第03次 | 同上，原始证据别名 `$PC68_R37_ENV03_RAW` | 支持安装与入口帮助均退出0；一次合成普通命令观察解析并原样转交同一对象，命令退出0，输入、消费者和服务前后不变。结果为 `PRECHECK_READY`；第二关口仍未完成，正式运行许可关闭 |
| 第37版传递目录预检第01次 | 同上，原始证据别名 `$PC68_R37_TRANSFER01_RAW` | 运行目录前缀不符合旧 R33 检查器要求，直接返回 `CASE_NOT_STARTED / transfer_root_requires_dedicated_private_tmp_run_directory`；没有结果文件、未发送请求。修正检查器接受计划规定的 R37 前缀后另用新目录重做 |
| 第37版传递目录预检第02次 | 同上，原始证据别名 `$PC68_R37_TRANSFER02_RAW` | 在计划规定的新根目录下发送一次标记用途请求；同一命令创建、读取核对、删除并确认标记缺席，退出0。传递目录请求前后均为空，消费者和服务未变，结果 `PASS / single_request_marker_lifecycle_verified`；没有运行教授业务或正式 `PC68-R1` |

第30版检查原文及修正历史见 `tests/runtime/evidence/issue68-r30-precheck-validation.json`、`tests/runtime/evidence/issue68-r30-review-fixes-validation.json`；保留每轮失败及通过的原始计数、恢复日志的可见范围和源码摘要，不把历史129项或更早轮次写成当前检查。原丢失日志的恢复仅覆盖原工具可见部分，不能称完整原始日志，不重跑冒充旧轮次。第26版对损坏样例审核依据的撤回不改写这些历史尝试。

前四次安装续试由用户在候选 `806066a` 推送后授权，均沿用固定产品提交、原支持安装命令及600秒预算；证书和传输设置仅作用于对应进程，证书验证保持开启。四次失败、恢复诊断、原始日志和独立审核结论见 `tests/runtime/evidence/issue68-r31-install-retry-review-20261007.md`，不覆盖先前超时。随后用户要求只重试安装。第05次在独立临时消费者中38.838秒退出0；锁文件固定到产品提交 `b39a4252e3ce473f8cdeedd2e12b0cf86d6f597d`，已安装 `contact_state.py` 摘要与产品源相同。独立限定复核确认上述数据一致，并确认修正后的锁文件摘要正确，见 `tests/runtime/evidence/issue68-r31-install-only-retry-review-20261007.md`。完整命令和输出摘要见新增安装证据。该轮没有运行入口帮助、合成评估或正式业务，因此只确认本次支持安装成功，不能据此宣布完整预检完成。

历史执行记录：随后按用户要求执行完整环境预检：第02次在依赖解析阶段达到600秒上限；一次只读 `git ls-remote` 成功后，第03次在新消费者中约46秒完成，安装10项依赖并配置1个模型上下文协议服务。固定产品提交与安装入口摘要一致，`--help` 退出0；唯一评估请求只解析并原样转交一份合成对象，输出退出0且通过同一调用关联检查。证据和原始摘要见 `tests/runtime/evidence/issue68-r31-environment-preflight-retry-20261007.json`。此次仅将环境预检更新为 `PRECHECK_READY`；当时正式合法临时传递位置覆盖仍未证明；本版当前目录证明状态见第4.1节，历史结论不改写。

历史第30版第03次实际请求模型为 `gpt-6-luna`、推理强度 `low`；当时服务工具为 `codex-cli 0.159.0-alpha.12.1`，本地准备工具 `codex-cli 0.160.1`。服务内部最终模型未公开，不宣称取得。第01、02次服务提交 `3fdfa9387140cfc2e2aa3af415f85015f79706d2` 仅为当次来源，不能充当本次实值。第31版完整预检第03次的实际配置、工具及服务前后摘要见其历史证据；`PRECHECK_READY` 和 `INCOMPLETE` 均只代表该历史轮次。第37版当前预检尝试及状态见 `tests/runtime/evidence/issue68-r37-preflight-validation-20261008.json`，在该记录确认的环境预检与传递目录预检均完成前，正式 PC68-R1 不得启动。

### 4.1 同一正式入口目录预检与正式准入对应

本节直接纳入第33版实际步骤及证据，取代第32版仅凭宿主合成动作证明目录可执行的安排。合成检查仍证明观察与判定；正式入口实际操作证明所选目录可用，两者不能互相替代。

正式目录操作仅创建、读取核对、删除一个无业务含义的标记；使用与R1相同的评估入口、项目配置来源、请求模型、推理设置、沙箱及隔离条件。不得由宿主程序代替这三项操作，不处理教授业务、不真实委派、不启停现有服务。原目录操作证据保留旧结论，但未证明第3.1节共享项目审批配置；只补新前提实际生效的依据，不额外验证审批系统自身或重复未受影响检查。

**已有证据及处理**：第33版第一次安装失败，原状态 `CASE_NOT_STARTED`，没有发出请求；连通性恢复后使用新消费者，第二次只发出一个请求。旧判定器误把普通根代理 `agentMessage` 当作委派，将结果记录为 `INVALID_TEST_EXECUTION`。修正判定器后对相同完整原始证据重新判读为 `PASS`，未覆盖原结果，未发送新请求。本次原件核对确认唯一命令在事件23435开始、23436结束、退出0，读取相符、删除后缺席、同根前后快照完整且为空，消费者和服务不变。这不是正式R1通过。

第30版离线复核从同一原始响应的 `output.app_server_events` 找到唯一根 `thread/started` 事件：`runtime_generation=1`、`runtime_seq=23390`。事件中的 `message.params.thread.model` 与 `message.params.thread.reasoningEffort` 分别报告 `gpt-6-luna` 和 `low`，两项状态均为 `OBSERVED`，与请求值一致。原第33版记录中的 `effective_model_status=NOT_EXPOSED_BY_CURRENT_SERVICE` 及旧判定均原样保留；本次补充只更新对该响应可见字段的离线观察，不覆盖原记录。此次没有新请求。

| 对象 | 固定来源 |
| --- | --- |
| 第33版实现及脱敏证据 | 测试提交 `d3d082667ecc19369c44c038a4147bcec8db9d4f`；`tests/runtime/evidence/issue68-r33-transfer-location-eval-preflight.json` |
| 实际请求摘要 | `88283d916a7af0b61bb20e4eb7459ab3ad989e262e005834514000445a5665cc` |
| 实际响应摘要 | `92fff452afbeddfaea2c530a8a664730aedec3e9a580325ab6c8233286ceb403` |
| 第37版实际目录预检 | `tests/runtime/evidence/issue68-r37-preflight-validation-20261008.json`，尝试及源码摘要见记录；对应原始证据别名 `$PC68_R37_TRANSFER01_RAW`、`$PC68_R37_TRANSFER02_RAW` |
| 原判定文件摘要 | `55119453767f338da60f3d307dc6c0fbc20b4cfe948ab7ed60eb458f6c533ad2`，原无效状态保留 |
| 修正后预检程序摘要 | `abab912f50a4d35df18369743c176bbb2761b4a2da19f445bd648070561e203d` |
| 原始材料定位 | 第二次运行 `50f0ee67-0ced-435a-bffb-2ba9c0ed475a` 的独占证据目录；公开别名 `$PC68_R33_RUN02_RAW`，实际位置由本地证据保管者提供，不在公开方案披露 |
| 第30版配置离线复核 | `tests/runtime/evidence/issue68-r33-effective-config-offline-recheck.json`；请求摘要 `88283d916a7af0b61bb20e4eb7459ab3ad989e262e005834514000445a5665cc`、响应摘要 `92fff452afbeddfaea2c530a8a664730aedec3e9a580325ab6c8233286ceb403`；修正后预检器和测试摘要见第1节 |

第33版定向验证共31项，当前实现提交及当时干净推送副本均退出0；来源、原始日志摘要及完整尝试保存在上述机器可读证据。第30版定向测试37项退出0，验证修正后的配置字段提取；离线复核不发送请求。两轮范围均不证明教授业务或正式委派已经通过。

**正式准入检查**：发送正式R1前，执行者记录实际 `PC68_TRANSFER_ROOT`，并与有效目录预检的请求、命令输出和前后快照中的根路径逐项对应；同时核对产品、共享资产、服务、请求构造器、沙箱和隔离条件。只复用真实证明同一所选目录且相关条件仍有效的证据。目录仍须为空、独占、不重叠，不得把预检消费者用作正式消费者。目录、权限或相关配置改变时，停止正式启动，交本地测试工程师补充受影响的最小预检及审核；不能以另一目录的成功记录放行。未变化的已完成检查不重复执行。若旧证据缺少可定位原件或无法完成对应核对，保持未完成状态，不推定通过。

目录预检入口及准备步骤如下。第36版续试R17使用旧产品提交 `b39a4252e3ce473f8cdeedd2e12b0cf86d6f597d`，其历史结果保留在 `tests/runtime/evidence/issue68-r36-project-approval-config-preflight-continuation-20261008.json`，不满足本版改为 `faab365d0be2bb66f2f285fdaa2927631dbf33f8` 后的版本绑定。因此 r37 必须在全新消费者和新独占传递目录中重做一次同范围的无业务目录预检；它只创建、读取、删除标记，不运行教授业务。目录名是该测试程序的既有输入限制，不是新增产品要求。

运行位置为包含本记录和预检程序的测试仓库根目录；先在三个已准备的本地检出目录中解析来源根路径，路径只保存在当前 shell。产品检出须固定在 `faab365d0be2bb66f2f285fdaa2927631dbf33f8`，共享夹具须固定在本次实现提交 `d160ecb403c0f9e9c153f4b8383302a4b67664ab`，评估服务检出须固定在 `3fdfa9387140cfc2e2aa3af415f85015f79706d2` 并使用其 `direnv` 环境；三者均须干净。`PC68_PRODUCT_CHECKOUT`、`PC68_SHARED_CHECKOUT` 和 `PC68_EVAL_CHECKOUT` 是本机已准备好的检出目录输入，不写入公开证据。运行下列准备命令时，当前目录必须是测试仓库根目录：

```sh
PC68_TEST_ROOT="$(pwd -P)"
: "${PC68_PRODUCT_CHECKOUT:?设置为已固定版本的产品检出目录}"
: "${PC68_SHARED_CHECKOUT:?设置为已固定版本的共享夹具检出目录}"
: "${PC68_EVAL_CHECKOUT:?设置为已固定版本的评估服务检出目录}"
PC68_PRODUCT_ROOT="$(cd "$PC68_PRODUCT_CHECKOUT" && pwd -P)"
PC68_SHARED_ROOT="$(cd "$PC68_SHARED_CHECKOUT" && pwd -P)"
PC68_EVAL_ROOT="$(cd "$PC68_EVAL_CHECKOUT" && pwd -P)"
test "$(git -C "$PC68_PRODUCT_ROOT" rev-parse HEAD)" = "faab365d0be2bb66f2f285fdaa2927631dbf33f8"
test -z "$(git -C "$PC68_PRODUCT_ROOT" status --porcelain)"
test "$(git -C "$PC68_SHARED_ROOT" rev-parse HEAD)" = "d160ecb403c0f9e9c153f4b8383302a4b67664ab"
test -z "$(git -C "$PC68_SHARED_ROOT" status --porcelain)"
test "$(direnv exec "$PC68_EVAL_ROOT" git -C "$PC68_EVAL_ROOT" rev-parse HEAD)" = "3fdfa9387140cfc2e2aa3af415f85015f79706d2"
test -z "$(direnv exec "$PC68_EVAL_ROOT" git -C "$PC68_EVAL_ROOT" status --porcelain)"

umask 077
PC68_R37_LOCATION_RUN_ROOT="$(mktemp -d /private/tmp/pc68-r37-transfer-eval-preflight-XXXXXX)"
mkdir "$PC68_R37_LOCATION_RUN_ROOT/transfer"
PC68_TRANSFER_ROOT="$PC68_R37_LOCATION_RUN_ROOT/transfer"
test -z "$(ls -A "$PC68_TRANSFER_ROOT")"
test "$(ls -A "$PC68_R37_LOCATION_RUN_ROOT")" = "transfer"
test ! -e "$PC68_R37_LOCATION_RUN_ROOT/evidence"
UV_CACHE_DIR="$PC68_LOCAL_UV_CACHE_ROOT" uv run --no-project python "$PC68_TEST_ROOT/.apm/skills/professor-contact/tests/runtime/preflight_issue68_transfer_location_eval_r33.py" \
  --producer-root "$PC68_PRODUCT_ROOT" \
  --fixture-root "$PC68_SHARED_ROOT" \
  --eval-direnv-root "$PC68_EVAL_ROOT" \
  --transfer-root "$PC68_TRANSFER_ROOT" \
  --output-dir "$PC68_R37_LOCATION_RUN_ROOT/evidence"
```

五个程序参数依次来自已核对版本的产品检出、共享夹具检出、评估服务 `direnv` 检出、新建运行目录中的空 `transfer/`，以及同一运行目录下尚不存在的 `evidence/`。输出目录由程序创建。读取结果时，不以进程退出码代替状态判定；退出码非零时仍检查已写出的结果文件：

```sh
jq '{state,reason,request_attempted,request_body_sha256,response_body_sha256,observation,integrity}' \
  "$PC68_R37_LOCATION_RUN_ROOT/evidence/preflight-result.json"
```


预检请求发送后不作同条件重试；请求未发送且前提经独立诊断恢复时，仅继续未完成的前置检查，使用新消费者并保留所有旧尝试。目录操作成功只确认必要执行能力。状态按本方案第6节分类；普通根代理消息不构成委派，真实委派或子线程事件须按固定判定程序处理。

已有离线重判只改变事件解释，原始材料完整，可以复用；不重发R09请求。第36版续试R17在用户后续授权后使用新消费者和新独占目录，支持安装耗时40秒，安装10个依赖和1个MCP服务，并保留 `on-request` 与 `auto_review`。R17仅发送一次新的无业务预检请求；唯一标记命令事件于序号26900开始、26901结束，退出码为0，创建、读取核对、删除及确认不存在均通过。请求前后传递目录快照完整、同根且为空，消费者与评估服务保持不变；机器结果为 `PASS / single_request_marker_lifecycle_verified`。原始证据别名为 `$PC68_R36_RUN17_RAW`。R17不重复R09请求，不启动正式R1，也不完成独立第二关口审核。

第37版实际目录预检的脱敏结果见 `tests/runtime/evidence/issue68-r37-preflight-validation-20261008.json`。首次尝试因运行根目录前缀验证而在请求前返回 `CASE_NOT_STARTED`；修正预检器后，第二次只发出一条标记用途请求，真实命令完成创建、读取核对、删除和确认缺席，退出码为0。相同传递目录的请求前后快照均完整且为空；消费者和服务前后摘要相同，项目审批设置为 `on-request` 与 `auto_review` 且与服务观察一致。原始记录分别保存在 `$PC68_R37_TRANSFER01_RAW` 和 `$PC68_R37_TRANSFER02_RAW` 对应的本地目录。该结果只证明选择目录的最小操作能力，不启动正式R1、不形成真实委派，也不替代 Gate 2。

## 5. 正式 PC68-R1 固定步骤

独立计划审核完成且本版 Gate 2 明确给出 `PASS / COMPLETE` 后，本地测试工程师才可继续完成正式准入检查；审核尚未通过时不得调用正式入口。当前准入状态记录在 `second_gate_status` 和审核材料中；历史运行记录中的布尔值只作记录，运行器不读取它们。调用前仍须通过真实输入来源、服务隔离和运行环境检查。正式消费者与输出另建，不能复用合成预检消费者。

工作目录为获批测试提交所在的仓库根目录，使用固定命令；下列大写变量按第3节实际目录取值，先保存到本次执行记录：

```sh
UV_CACHE_DIR="$PC68_LOCAL_UV_CACHE_ROOT" uv run --no-project python .apm/skills/professor-contact/tests/runtime/run_issue68_stage5_routing_r19_codex.py \
  --producer-root "$PC68_PRODUCT_ROOT" --producer-sha faab365d0be2bb66f2f285fdaa2927631dbf33f8 \
  --fixture-root "$PC68_SHARED_ROOT" --fixture-sha d160ecb403c0f9e9c153f4b8383302a4b67664ab \
  --eval-direnv-root "$PC68_EVAL_ROOT" --output-dir "$PC68_OUTPUT_ROOT" \
  --transfer-location-root "$PC68_TRANSFER_ROOT"
```

启动边界是完成第二关口冻结及第4.1节目录预检对应检查，并由正式运行器完成版本、干净消费者安装、输入与输出隔离、六项环境证据及观察检查后，写入本次启动记录并发送唯一正式请求。边界前失败是 `CASE_NOT_STARTED`。正式请求一旦发送，不换模型、不重试、不另发评估请求代替委派。

六项实际事实来源：`model`取本次请求；`executor`取实际编码执行分支的函数/模块和源文件摘要；`entrypoint`取已安装 `contact_state.py` 路径/摘要；`isolation`取服务与存储前后快照；`shared_assets`取固定产品/共享干净提交及锁文件摘要；`service_version`取本次只读服务干净提交并前后比较。监听进程只作服务来源，不能冒充执行器。预检记录验证来源可用，正式请求仍重新保存本次实值到 `runtime-environment-evidence.json`、`input-evidence-preflight.json`、`provenance.json`，不拿旧预检替代本次记录。


步骤按表中顺序执行。任何前置门未通过即停止，不得跳到下一步。PC68-R1 只允许一次正式服务请求，不重试，不更换模型、执行器、服务或入口来寻找成功。

| 步骤 | 操作和实际输入来源 | 必须保存的直接证据及核对条件 | 停止条件 |
| --- | --- | --- | --- |
| 0. 冻结与准入 | 使用唯一完整测试实现版本、获批产品目标和本版计划及本文完整记录；完成第二关口审核及第4节全部必要预检，按第4.1节核对正式选定目录与有效预检来源 | 审核指定版本、产品与测试完整 SHA、入口及判定程序版本；确认正式入口类别未改，产品代码未为测试修改 | 第二关口未完成时先记 `CASE_NOT_STARTED`，仅禁止正式业务请求；候选 SHA 未固定、预检不通过或任一必填事实未知时也不启动 PC68-R1。当前状态即为此门未通过 |
| 1. 准备输入 | 建立两位教授独立本地包、合法显式选择、无关行、坏包与缺核验状态；保存独立预期。`canonical-choices.json` 顶层必须是用户提供的 `choices` 数组本身；不得把含 `choices`、`mode`、`template` 或其他请求元数据的外层对象保存为选择行。不得提前分配、拆分选择或制作教授交接文件 | 每个原始输入的来源、路径、内容校验值；教授目录和邮件编号原值；本地状态及隔离目录的执行前快照；独立预期与原始选择数组之间不重叠且不从被测分配输出反推 | 输入不完整、预期并非独立于被测输出、目标或目录冲突、选择文件不是原始选择数组、准备阶段写入根代理交接/分配结果：停止并修复测试准备，不运行正式请求 |
| 2. 检查安装和隔离 | 按固定产品提交支持的安装方式建立干净消费者（关口前最小安装已由独立预检检查；正式运行仍新建消费者）；记录其 `contact_state.py` 路径和哈希；记录 Codex dispatch 身份及源文件哈希；通过只读请求前快照记录服务版本和隔离；检查空输出目录 | 产品及消费者版本、安装入口路径和哈希；dispatch 函数/模块身份与 dispatcher/runner SHA-256；目录为空且彼此不重叠；服务请求前 provenance 快照 | 关口前可以经独立预检入口只读检查服务及支持安装；正式请求仍须第二关口完整通过；安装失败、产品版本不符、目录不干净或隔离不成立：`CASE_NOT_STARTED`；不得直接运行命令行工具替代入口，也不得启动或重启评估服务 |
| 3. 发送唯一正式请求 | 通过评估服务和干净消费者组成的正式入口执行本次固定请求；使用第 3 节记录的模型、Codex dispatch、已安装 `contact_state.py` 入口及请求前服务版本 | 请求与响应原件、根线程和运行标识、请求次数、入口日志；确认恰好一次请求 | 任何前置配置改变或服务不可用时不发送；请求一旦发送，不重发完整业务请求。服务、权限或模型问题按实际外部阻断保留 |
| 4. 根代理发现 | 根代理通过原有只读发现路径检查本地包；坏包不得影响合法教授包 | 正式根线程的 `commandExecution` 调用编号、实际线程、运行代次、事件顺序和 `aggregatedOutput`；输出应区分两位合法教授与坏包，且发现不带 `--emit-choices-scope`。后续分配所用教授路径必须与此处结构化发现结果逐字符一致 | 输出缺失或不能归属时按证据缺失/无效分类；真实有效输出显示业务越界时判产品失败 |
| 5. 根代理分配 | 根代理在正式根线程上仅发出一次 `stage5-partition-choices` 调用，一次提交本次请求的全部教授；直接使用第4步发现路径，不翻译、规范化或改写。不得在失败后重试、改分配单个教授或追加第二次分配 | 调用的线程、运行代次、`commandExecution.id`、参数及真实 `aggregatedOutput`；调用参数路径与第4步结构化发现值逐字符一致；完整分配行中的教授目录、包、目标和所有选择字段与第1步独立预期逐字段相同；两位教授均出现各自非空且正确归属的 `choices_rows`；分配完成事件先于任一教授业务调用 | 分配调用不是一次完整提交、路径被改写、出现追加/重试/子集分配、选择归属错误或任一教授业务早于分配完成：有直接有效证据时 `FAIL_PRODUCT`。没有支持的调用观察时不得推断产品行为，按阻断或无效证据处理 |
| 6. 正式委派 | 根代理按两位教授分别委派；线程身份只采用共享适配器确认的正式 `spawnAgent` 关系 | `dispatch.thread_relations` 中 `tool=spawnAgent` 且 `sender_thread_id` 为根线程的两条正式边；线程 ID 与运行代次。以同次 `subAgentActivity` 唯一绑定 `agentThreadId` 到 `agentPath`；`agentPath` 只作回执关联键 | 没有正式关系但运行未证明实际调用时不得宣称委派故障；缺少受支持线程关系为 `BLOCKED` 或 `NOT TESTED`，按实际停止原因说明。单一 child 被多个不同 path 绑定为 `INVALID_TEST_EXECUTION` |
| 7. 教授交接与实际读取 | 根代理在本次运行中生成各自 `owner_input_file`。各教授代理沿原有正常路径解析自己的 JSON；固定捕获器只读复制该次解析所得对象，后续业务参数继续取同一个对象。根和教授调用的每条 `uv run` 命令都须以前置 `UV_CACHE_DIR='<PC68_UV_CACHE_ROOT绝对路径>'` 运行 | 每次本地捕获信封含 `pc68_fixed_capture`、`pc68_actual_input_observation`、`stage5_invocation`、`stage5_raw_stdout`、`stage5_process`、`stage5_plan`、`return_code`。同一 `capture_id` 关联本地读取、实际 CLI `argv`、stdout/stderr 摘要和退出码；verifier 从独立 `commandExecution.command` 校验固定捕获器调用路径、唯一允许的缓存前缀和参数，脚本摘要从固定仓库源码校验。另关联 `runtime_generation`、正式教授 `thread_id`、`commandExecution.id`、教授目录、`source_step=owner_input_json_parse`、`business_step=stage5-plan` | 整个 `stage5_invocation` 缺失为 `BLOCKED_OBSERVABILITY`；对象存在但必需 `argv` 缺失或损坏为 `INVALID_EVIDENCE`。缓存路径与本次声明不符、字段关联不一致、捕获器调用不符或运行/线程/调用关联歧义为 `INVALID_EVIDENCE` |
| 8. 首次计划与数据边界 | 同一教授、同一解析对象驱动原有 `stage5-plan`；本例首次调用不带 `--result` 或 `--choices`。业务程序必须是消费者内正式程序 | 同一 `commandExecution` 中实际 `stage5_invocation.argv` 完整字符串数组、`stage5_raw_stdout`、与其一致的 `stage5_plan` 结构化结果及 `return_code`；按原字段检查 `email_pack`、`emails`、`jobs[].model_input`、核验状态。将读取对象与本次根分配对应项、本地包独立预期逐字段比较，并检查没有兄弟教授数据、改写路径或编号。固定夹具要求首次调用退出码为 0、顶层 `status=ok`，且该教授的核验值为 `needs_recheck:missing` | 有效实际证据证明错包、错编号、选择错配、兄弟数据、`--choices-scope`、首调含 `--result`/`--choices` 或首次计划的固定核验结果不符：`FAIL_PRODUCT`。只有命令文字出现参数不能证明实际调用参数。该核验结果是步骤9教授终态的输入，不得据此改写首次 CLI 回执 |
| 9. 教授结果与根消费 | 根代理等待并分别消费正式教授线程真实返回；每位教授结果独立保留。对本固定夹具，`needs_recheck:missing` 必须映射为教授终态 `status=needs_refresh / reason_code=verify_missing`；不得改成 `status=ok`、其他状态或其他原因。教授任务必须在自己的最终结果顶层给出 `professor_dir`、`status`、`reason_code`，随后根回执原样保留该三元组 | 正式 child 自身线程的原始最终结果；同一运行、当前 root turn 的 `rawResponseItem/completed` `agent_message` 回执；`recipient=/root`、`author` 等于唯一 `agentPath`，正文为规定的 `Message Type: FINAL_ANSWER`、`Task name: /root`、`Sender: <path>`、`Payload:` 和唯一顶层 JSON。Payload 顶层含 `professor_dir`、`status`、`reason_code`；回执 `runtime_seq` 是消费点。判定器将 child 结果与该 owner 的 `manifest.expected_result` 中 `status`、`reason_code` 及清单 `professor_dir` 比较，并再核对根回执与 child 结果完全一致 | child 无 path 或无合法回执为阻断；多个不同 outcome 或 path 映射歧义为无效证据；有实际 child 结果但不等于固定预期，或合法回执与 child 自身结果不一致：`FAIL_PRODUCT`。`child_thread_reads`、等待消息、完成诊断、角色自述和身份诊断均不能代替消费回执 |
| 10. 总览和最终消息 | 根代理消费完两位教授结果后，在根线程独立调用一次 `stage5-rebuild-overview` | 唯一总览调用的 `commandExecution.aggregatedOutput` 是结果唯一来源；开始顺序晚于每个正式教授结果消费点。当前根线程最终 `final_answer` 分别原样报告每位教授结果及完整总览结果；对象按业务字段识别，不要求固定包装键 | 提前或重复总览调用、改写教授结果、漏报或改写总览、结果双重归属冲突：有效证据证明时为 `FAIL_PRODUCT`。输出缺失为观察阻断，损坏/冲突/无法唯一归属为无效证据 |
| 11. 后置检查与清理 | 请求结束后检查本地状态、传递文件、请求专用 `uv` 缓存和服务隔离；只清理本请求临时数据 | 本地状态前后快照、相关文件内容/校验值、同请求前记录、实际使用、后记录与保护数据组合；证明没有跨教授写入、总览反向修改教授结果，观察副本在原文件清理后仍可复查；请求后服务 provenance 与请求前一致；缓存目录与传递位置分别核验和清理 | 服务进程或存储隔离变化、证据被污染或不能归属为无效执行；真实跨教授写入为产品失败。清理不能删除其他请求数据，清理错误不得改写教授结果；本次缓存未清理或实际路径越界时按执行证据分类，不能报告生命周期完整通过 |

正式线程集合只由共享适配器 @16 的正式 spawn 关系确定。`subAgentActivity` 不能创建或升级线程所有权；`requested_role`、加载身份、诊断事件及提示词内容均不构成正式归属证据。最终根消息仅选当前运行、当前根线程、当前 turn 的唯一 `final_answer`；不能从其他线程、旧 turn、评论阶段、历史输出或嵌套诊断补缺。

根事件须绑定当前根轮次；正式教授调用开始/完成须具备自身相同且非空的轮次、正式根子关系及相同运行代次，教授轮次不必等于根轮次。运行代次与JSON类型都要一致，不能把整数、字符串或布尔值转换后视为同一身份。真实损坏或归属冲突不能提供产品失败事实。

### 文件生命周期的固定收集与组合方法

正式运行器仍在发送请求前调用 `issue68_lifecycle.collect_before(manifest, consumer)` 并保存 `codex/lifecycle.before.json`；`bind_before(before, saved_request)` 将它绑定唯一请求。第32版在同一 `manifest` 中登记唯一 `transfer_location_root`，其规范化路径同时作为唯一额外观察根，因此请求前后均完整记录业务目录、独占消费者和该传递目录。判定前 `collect_lifecycle(before, manifest, consumer, response, input_verifier)` 保存 `codex/lifecycle-evidence.json`，写入 `fixture-manifest.json` 的 `lifecycle_evidence` 和 `lifecycle_boundary`；异常退出尽量保留后置材料，不补造没有发生的业务。正式判定入口 `verify_bound_lifecycle(evidence, manifest, response, adapter, input_verifier)` 重新从原始事件及固定捕获来源构建实际使用事实，核对请求关联和保存材料，再调用 `verify_lifecycle`。合成预检不证明正式线程、实际根代理转交或教授业务结果。

观察固定覆盖本次 `manifest.program_root`、独占消费者目录及唯一额外观察根 `manifest.transfer_location_root`；`snapshot_tree` 记录全部相对路径、文件的字节数与摘要、目录、符号链接目标及根目录存在状态，不沿符号链接扩大读取。位置声明指示根代理将目录交给负责的教授执行者；产品决定具体文件名与布局。漏扫、无法读取或声明位置未覆盖时记录证明缺口；范围外位置按观察阻断处理，不把合法范围外路径判产品失败，不扫描用户主目录或其他请求。观察程序不分配业务选择或指导教授工作步骤。

准备程序的 `protected_other_request_files` 是请求前已存在的被动合成保护文件，不启动第二次真实请求。教授本地状态、输出、已有输入、消费者安装文件和保护数据都以完整前后记录比较；只有本例允许的总览派生变化可按原要求认可。保护文件内容摘要、字节数及路径不得改变，也不得删除。证据存储在独占输出目录，业务清理不得删除证据副本。

判定对每个实际形成的传递物连接以下事实：

1. 请求前的完整目录记录证明它尚不存在；前记录及记录范围与唯一请求绑定。
2. 中间真实来源证明它本次确实形成并用于对应步骤。根代理原始选择文件由本次分配读取及真实返回的 `choices_path` 证明实际使用；完整分配文件可用原产品成功 `stage5-partition-choices --out` 真实返回中的 `out_path` 及源码先写文件再返回关系证明形成，不要求额外读取整份文件。教授交接以正式教授线程正常解析那一次实际读取的固定捕获副本证明存在、可读及内容；不从命令字面量、提示词或事后读取推算。
3. 本请求及相应读取者结束后取得同范围的完整记录，证明本请求传递物最终缺席。结合隔离、无测试清理或其他进程介入、实际使用顺序和教授结果消费/报告，才归因产品结束后的清理。后置缺席是直接状态事实，不要求识别删除命令。
4. 教授结果仍与实际回执和最终报告一致，清理错误没有回滚或改写结果；其他请求合成保护数据及不允许变化的本地文件保持前记录内容。

本例实际路径为原始选择、真实形成的完整分配输出及各 `owner_input_file`；合法核验早停未形成后续教授选择或结果传递文件时，不要求补造它们。确实发生的其他传递按实际使用与本请求来源纳入，不按文件后缀扫描和删除。清理清单还须涵盖已形成但未成功交付或读取的本请求传递文件：依据请求独占范围、正式产物来源和前后差别确认用途与归属，不能只列成功读取的路径而忽略失败留下的文件。归属或清单无法确定时不通过，不把日志和测试证据任意列为传递物。`collect_lifecycle` 从分配返回、实际教授读取和可归属交付尝试构造 `partition_returns`、`reads`、`file_operations`；`verify_lifecycle` 检查完整目录的新增条目，不能用任意后缀推定它们都是传递文件，未归属条目不能支持完整清理证明。

正常整链且保护数据不变才认可该证明。有效关联证据直接证明残留、旧请求文件被复用、保护数据删除/改写或结果受清理影响时判产品失败；真实缺失、漏扫或无实际使用不能通过，损坏、矛盾或错请求按无效执行分类，外部观察暂不可用按启动边界判未启动或阻断。早期传递失败保留已形成文件的状态和真实失败，不伪造完整成功链，不以缺少后续教授调用遮蔽已经有效证明的违规。

`file_operation` 对有限写入、读取和删除命令的解析及原始记录只作辅助诊断；不能因为不识别程序化写入或清理就拒绝满足上述组合条件的有效执行。创建或删除事件不是通过硬门槛，不要求产品选择某种语言、重定向形式或辅助函数。第30版这项硬门槛与“任意脚本副作用未知即必须阻断”的旧结论已由后续测试计划取代。第32版补齐独占传递目录的声明、请求绑定、同根观察和预检；不新增业务操作或限定实际文件名和布局。

第03、04次原始响应合计4个命令，字段解析显示均为唯一开始/结束且两侧命令相同；没有真实重复开始或配对命令冲突。原第04次执行入口摘要为 `dce98777dd1cc05b2bf70644b268cced79df31a0f57f6b19a97560ac74cff288`，当时收集器摘要为 `718f84c3a7b51996b6adb06c07ee9d1a667b0af3084b3d084321d6e1eb276cef`；后续两次只读重解析的摘要、材料及来源保留于第04次投影，不把后来的程序摘要冒充原执行版本。上述来源只供能力及历史复查，第31版组合验证与最小预检分别保留新轮次来源。


## 6. 六终态、机器标签与总体分类


本版沿用以下六种正式终态用于整例验收。逐教授保留各自真实业务结果的 `status`、`reason_code`、退出码和原始证据，核对根代理分别消费并原样报告；不额外要求每位教授生成六种测试终态。教授业务状态（例如缺核验早停）与判定程序的整例机器标签分别记录，退出码本身不能替代分类依据。

| 本版正式终态 | 机器标签或记录方式 | 适用条件 |
| --- | --- | --- |
| `PASS` | 整例机器标签 `PASS` | 本例负责的全部事实都有直接、有效、可归属且一致的证据；合法核验早停后的后续业务事实不在本次证明范围内，不能假称已发生 |
| `FAIL` | 整例机器标签 `FAIL_PRODUCT` | 有效、直接证据证明产品违反冻结要求，包括根代理或教授行为中的实际输入错配、兄弟数据、路径/编号改写、越序分配、错误回执消费、总览早于结果消费或改写结果 |
| `BLOCKED` | `BLOCKED_OBSERVABILITY`，或保留外部阻断的原始机器标签和原因码 | 已开始有效执行，但必需事实因支持的观察条件或外部服务、模型、权限等条件无法判断；没有有效证据证明产品失败。启动前受阻归未启动 |
| `NOT TESTED` | `NOT_TESTED`，按实际未执行范围说明 | 声明路径没有实际发生且非产品违规、外部阻断或测试缺陷；合法核验保护阻止的后续业务须明确未执行，不要求其出现，也不能假称已经通过 |
| `INVALID_TEST_EXECUTION` | `INVALID_EVIDENCE` 或执行器对应无效标签 | 输入、执行或证据被污染、矛盾、损坏或无法归属；已知设计缺口须在第二关口修正 |
| `CASE_NOT_STARTED` | `CASE_NOT_STARTED` | 正式用例未越过固定启动边界，如第二关口未通过、安装失败、版本不符或隔离检查未通过 |

以下证据细分不得互换：

- 整个 `stage5_invocation` 字段缺失，意味着必需调用观察缺失，机器状态为 `BLOCKED_OBSERVABILITY`，正式请求前停止。
- `stage5_invocation` 对象存在，但必需 `argv` 缺失或损坏，属于观察结构无效，机器状态为 `INVALID_EVIDENCE`。
- `argv` 被真实捕获且证明首次调用带有禁止的 `--result` 或 `--choices`，或真实结构化业务输出证明错包、错编号、业务数据错配或兄弟数据，属于 `FAIL_PRODUCT`。
- 只有命令文字含这些参数，不能证明实际 argv，也不能据此判产品失败；根据实际信封是整项缺失还是结构损坏，分别阻断或判无效。
- 没有正式线程关系证据，不单凭零条关系推断产品委派故障；缺 path 映射为 `BLOCKED_OBSERVABILITY/root_result_consumption_unobservable`，一个 child 对应多个不同 path 为 `INVALID_EVIDENCE/child_agent_path_mapping_ambiguous`。合法回执缺失为阻断，多份不同结果为无效，回执与 child 自身结果不同为 `FAIL_PRODUCT/root_receipt_payload_changed`。

整例分类依据本次实际执行及证据，使用上表映射，不另造六种状态的优先顺序。只要有效直接证据已确认根代理或任何教授的产品违规，整例保留 `FAIL_PRODUCT`→`FAIL`；其他教授缺观察、缺回执或证据有歧义不能把已确证产品失败降为阻断或无效。没有确证违规时，按实际启动边界、观察缺失、无效证据、外部阻断及证明完成情况记录整例终态；同时原样保留逐教授业务结果及具体未执行范围。

## 7. 输入与结果的比较规则

根代理分配返回是本次分配实际输出；它必须与独立预期比较，但本身不代表教授收到或读取了分配。每位教授实际输入证明需连接下列四个对象：

1. 本次根代理真实分配输出中的对应教授项。
2. 根代理本次生成的该教授 `owner_input_file`。
3. 教授线程原有 JSON 解析动作同次复制的只读对象。
4. 同一命令调用中的真实 `stage5_invocation.argv` 和 `stage5_plan` 结构化输出。

`pc68_actual_input_observation` 采用 `issue-68-test-plan-r25-owner-input-v2`。`pc68_fixed_capture` 记录固定捕获源码摘要、一次读取的 owner 文件和解析对象摘要；`stage5_invocation` 和 `stage5_process` 用相同 `capture_id` 关联实际 argv、stdout/stderr 摘要及退出码；`stage5_raw_stdout` 是原始 stdout，`stage5_plan` 必须与解析该 stdout 得到的对象一致，`return_code` 是同次调用退出码。正式线程证据应保存在 `output.app_server_events.commandExecution.aggregatedOutput`，并关联 `output.runtime_generation`、正式线程 `thread_id`、`commandExecution.id`、教授目录和步骤名。合成预检不含这些正式运行事实；它们由一次获批候选的 PC68-R1 采集。

运行代次接受JSON整数及历史字符串；关联时同时比较值及JSON类型，不将整数 `1`、字符串 `"1"` 或布尔值 `true` 视为同一次运行。独立根调用有真实有效违规证据时，判定先保留产品失败，再记录教授观察缺口，不能以缺口遮蔽已经成立的失败。

结构化选择按字段和值比较，不要求缩进、键顺序或换行一致；教授目录、包路径和邮件编号按原字符串比较，不可规范化后掩盖改写。命令文字、命令中的 JSON/Python 字面量、临时路径、准备阶段文件、manifest 预期值、事后重读文件、最终业务结果、教授自述、加密提示词及无关输出均不能替代实际输入证据。计划输出只证明它明确返回的真实字段；它不证明该调用没有返回或记录的数据。

## 8. 历史结果与复验依赖

D1采用第二十六版明确保留的 `REUSE_PRIOR_PASS`。可访问脱敏证据为 `tests/runtime/evidence/issue68-d1-r29-history.json`，来源运行 `pc68-d1-r29-20261006`，原始包保存在该轮本地专用临时目录。原产品 `35f2785b4d13783683860db910a36add2347bd29`、原测试 `e931ab22fbe492bdf0c4ecb74e906d2c23dfce23`，43唯一组件与7证明旧通过；原 `execution_kind=preflight` 原样保留，不能记成当前执行。第二十六版沿用第二十五版的影响分析：目标产品有关差异只在帮助与代理调用说明，本次只整合R1目录预检及执行交接，P1—P7依赖未变，故复用旧结果，不本轮重跑D1。

下列为完整必要组件映射，亦作为未来依赖变化时的定位；不是本轮重新执行记录。


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

## 9. 固定判定入口、复验与交付边界

正常测试由运行器调用固定判定程序，保存原始记录和最终结论后完成。正式执行者和审核者不需要为同一次测试再运行判定命令。正式运行入口已实现第3.1节要求的实际审批配置检查；本次不要求修改测试程序或增加检查步骤。

只有测试规则第5节允许的情形，才使用旧原始记录重新判定：变化仅影响如何解释结果，且完整、可信的旧记录已经包含当前判定所需的全部事实。审核者先说明变化、受影响用例和选择 `REJUDGE_PRIOR_EVIDENCE` 的理由；本地测试工程师提供适用的完整判定程序及固定命令，独立审核冻结后，由本地执行代理执行并记录程序版本、命令和新结果。目的仅是确认旧记录在变更后的判定规则下是否仍然通过，不是重复正常测试的收尾步骤。新结果单独保存，不覆盖原结论，不补写缺失事件，也不发送新业务请求。

变化影响执行行为、输入、测试环境、入口、可取得的证据或运行前提时，必须重新执行受影响用例，不能靠重新判定旧记录补齐。本版D1复用未受影响的旧通过结果，R1要求当前执行，均不采用旧记录重新判定；因此本文不提供额外重新判定命令。第34版所列独立命令只检查业务和生命周期，不能代替包含第3.1节运行前提检查的正式结论，现从计划中删除。第36版修正安装前配置准备、安装后保留核验及预检缓存路径；这些执行步骤不改变证明对象和业务通过条件。

D1依赖：P1本地来源/迁移；P2目标过滤/自身非法；P3整批/回滚；P4教授交易/校验/状态；P5总览派生/人工保护；P6发现读取；P7分配/归属/歧义/原值/包装。只有变化命中具体依赖才重开对应证明，不因提交编号变化全量重跑。

R1为 `EXECUTE_CURRENT`：观察、判定、输入和产品调用说明变化直接影响真实数据传递证明，旧失败/阻断运行不能重判补齐未发生的教授业务。依赖还包括支持安装、正式线程关系、结果回执、当前最终消息、独立总览输出、六项环境来源及文件隔离/清理。每次相关变化仅重新做受影响预检及直接关联检查，再由审核者冻结；正式执行者不得临场修测。外部故障只保留具体缺口，不改产品或降低证明要求。

正式输出须保存完整请求响应与原始事件、线程图、每次观察信封和实际参数/标准输出、根分配及消费回执、总览输出、输入与文件前后摘要、消费者及产品/共享/服务版本、服务前后来源与隔离、机器状态和六终态映射。原传递文件清理后证据副本仍可复查；清理仅本请求数据，不影响教授结果。保留所有历史尝试，不以二次运行覆盖失败。

第34版待审变化为第3.1节共享项目审批配置来源和实现职责，删除第32版额外冻结的接线与审批取证要求。变化影响PC68-R1的运行前提及相应预检；按测试规则第6.2节只重审这些依赖和直接连带影响，不重开第一关口或第十三版实施计划。D1和未变生命周期、输入、委派、消费及总览判定设计保留原来源。第35版明确正常测试与旧记录重新判定的区别，删除第9节无用途的额外命令。第36版修正配置准备顺序和预检缓存位置，并记录 R07–R16 的安装及 R09 请求观察；不改变业务断言或通过条件。

第31版可移植性修正及独立来源为 `tests/runtime/evidence/issue68-r31-lifecycle-combination-portability-validation.json`：无历史参数六场景就绪，可选历史参数六场景就绪，既存输出目录拒绝退出2且所有证据摘要保持不变，4项回归退出0。首次回归退出1源于新增合成样例漏写运行标识，该失败及修正后日志摘要分别保留；不覆盖旧组合预检。该轮入口摘要为 `4d5122a373aa775248d0f55d8ab53177bfc90d9fa74a2901952f3acb7b2890c5`。

最终源码绑定见 `tests/runtime/evidence/issue68-r31-lifecycle-combination-final-validation.json`：在该轮本地专用临时目录执行，退出0，六场景全部符合第26版预期，未使用写删诊断事件；12项环境判定检查退出0。最早61项组合验证与可移植性验证的生命周期摘要属于各自历史源码，不能冒充最终修正后的来源。最终组合预检仍使用真实本地子进程和合成运行信封，不是正式评估请求。

保护既有条目的修正及关联复验见 `tests/runtime/evidence/issue68-r31-protected-data-fix-validation.json`，五轮分别保留：缓存不可写导致0项未启动；66项执行中13个断言失败；修正教授结果样例后1项反例仍显示错误通过；首次判定修正126项中30个程序错误；最终126项退出0。中间重建源码摘要明确标注重建来源，不称现场捕获。最终逻辑比较全部既有文件、目录及符号链接，业务输出或传递声明不能豁免旧条目；合法新增业务输出仍可按实际来源认可。这126项与早先61项、56项、可移植性4项有重合，不能相加为独立总数。

先前完成度检查来源及已知缺口见 `tests/runtime/evidence/issue68-r31-completion-review.md`。该次独立只读审核已复核两项代码修正，并完成当时最终文档、契约及126项新证据的归并复核，确认材料一致、检查范围完整；当时角色实现结论为部分完成，除合法位置覆盖和安装超时两项已知缺口，没有新增必须修复问题。该审核不覆盖随后新增的四次安装重试证据；另一次历史独立只读复核已完成，范围仅四轮安装及直接关联文档契约，确认原始命令、退出码、日志与证据一致，独立诊断未替代安装，无新增必须修正问题。实际复核范围及部分完成结论由 `tests/runtime/evidence/issue68-r31-install-retry-review-20261007.md` 单独记录。两份记录均不授予第二关口通过或正式运行许可。

| 第32版历史源码（当前是否复用须核对固定候选） | SHA-256摘要 |
| --- | --- |
| `tests/runtime/issue68_lifecycle.py` | `f9fc8b13f26b2826127aaa371eaf6b93479cba279c2e7b4f929b487a2bb8329e` |
| `tests/runtime/issue68_transfer_location.py` | `62de870ac12ad727bb9d65221a1aac918a68bd4bbe94bb9acb421872c19b913e` |
| `tests/runtime/run_issue68_stage5_routing_r19_codex.py` | `93e4a30c23d4de374142bb1a5b908837bbb703dd7a7f3ba501672851a24e5481` |
| `tests/runtime/preflight_issue68_transfer_location_r32.py` | `b6d513b4e13ba9701045e95cf4371dc563b34ad41ef3afda679a8412890af739` |
| `tests/test_issue68_transfer_location.py` | `ddd8b2449e24eff8ffc6718faa812dcb648128c0ab89bb8dcf79f88de3d3c790` |

| 第31版历史源码 | SHA-256摘要 |
| --- | --- |
| `tests/runtime/issue68_lifecycle.py` | `f9fc8b13f26b2826127aaa371eaf6b93479cba279c2e7b4f929b487a2bb8329e` |
| `tests/runtime/preflight_issue68_lifecycle_combination_r31.py` | `4d5122a373aa775248d0f55d8ab53177bfc90d9fa74a2901952f3acb7b2890c5` |
| `tests/runtime/run_issue68_stage5_routing_r19_codex.py` | `ebf9d866a4ca7c5a7392fbbb0b93d8e07fcf30b176d3badb26f44f6070fd962a` |
| `tests/test_issue68_lifecycle.py` | `6a18f5ff39bb344a6f2a76eed361dbe2ca8fc75466c357d5c36a04068c27d988` |
| `tests/test_issue68_lifecycle_integration.py` | `a32a366e8eaec90ab6c5887320308ebe2fd97c1ad3ace76f49c7fb4c382cc5f1` |

此前第31版完整环境预检第01次的主源码摘要前后均为 `3cc9cf5d2a62d1248ffa999cddb65d894a83d40f4e40dab1bfec942e1495a631`。执行时运行器摘要为 `6a0634c6d58d4e32631bafa3d8058130bb6fa0a889ed231cab2da2ddf5dd4a24`，结束时为 `ebf9d866a4ca7c5a7392fbbb0b93d8e07fcf30b176d3badb26f44f6070fd962a`；并行改动只同步测试版本标识，该次安装阶段停止，没有发出观察请求。原记录继续保留在 `tests/runtime/evidence/issue68-r31-environment-precheck.json`。第05次独立安装的原始日志、锁文件及结果摘要保存在当次本地专用临时目录；第02、03次完整预检的新源码、请求、响应、帮助和完整性摘要见新增重试证据，不覆盖前次失败。

第32版历史新增位置声明、实际请求绑定、清单快照和同一传递目录的请求前后观察。合成预检证据见 `tests/runtime/evidence/issue68-r32-transfer-location-preflight.json`，七个场景符合本版预期，命令退出0；位置、运行器、预检及单测的源码摘要均随证据保存。定向测试11项、R19判定56项、生命周期70项、运行配方11项均退出0。该证据不含实际教授线程或正式请求。

当前合成位置判定材料按未变源码和数据关系复用；第31版环境及第33版目录证据保留其历史来源和真实证明范围。第34版原预检记录见 `tests/runtime/evidence/issue68-r34-project-approval-config-preflight.json`，原始记录别名为 `$PC68_R34_RUN01_RAW`。用户报告外部 `apm install` 正常，并授权网络停滞后继续重试。R02–R06 的五个新消费者均在安装阶段失败：两次在600秒后退出124，三次在依赖克隆时遇到 TLS 连接断开。R07 又因 `fetch-pack` 内容传输中断而失败。R08 与 R09 均完成支持安装；R08 暴露配置助手必须先于 APM 安装运行的顺序错误，R09 修正后在安装前创建项目配置并通过安装后保留检查。R09 的服务响应实际报告 `on-request` 和 `auto_review`，但唯一一次合成请求未观察到标记命令。响应中的 agentMessage 自述用户级缓存权限错误和退出码 2；由于没有对应 commandExecution 事件或原始 uv 错误输出，该自述未经机器事件证实。机器结论为 `NOT TESTED / marker_command_not_observed`。R10 在新消费者用32.1秒成功安装10个依赖和1个MCP服务。R11 在依赖解析停滞710.7秒后被人工中断，退出130；它超出第4节600秒安装保护窗口110.7秒，记为执行偏离，不能按符合时限的安装尝试报告。R12 因 `knowledge-tools` 的 HTTPS/TLS 连接意外中断而于23.5秒失败；R13 因 `paper-analysis` 的 HTTPS/TLS 连接意外中断而于23.3秒失败。R14 在全新消费者用28.5秒安装10个依赖和1个MCP服务，并确认两个项目审批值安装后保持不变。R15 在解析固定产品时于300秒由包装器提前截止，未达到第4节600秒保护窗口，记为执行偏离；其配置值保持不变。R16 在全新消费者于49.5秒安装10个依赖和1个MCP服务，安装后仍读到 `on-request` 与 `auto_review`。R10–R16 均未发送评估请求。一次误从测试检出目录启动的安装已排除并清理，另一次R15包装器因权限不足未启动APM，也从安装次数中排除；原因与记录见 continuation JSON 的 `excluded_invocations`。初始本地生命周期与目录接线测试失败及其后续通过记录也已在该 JSON 中并列登记。R09 的请求已发送，不按第4节重发，且不构成目录操作通过。R02–R06 原始材料及 R07–R16 和 P01–P03 安装、顺序探针摘要分别见 `tests/runtime/evidence/issue68-r34-project-approval-config-preflight-retries-20261008.json` 与 `tests/runtime/evidence/issue68-r36-project-approval-config-preflight-continuation-20261008.json`。正式 `PC68-R1` 未执行。

R17是在R16安装成功后新增的单次标记目录预检，结果为 `PASS / single_request_marker_lifecycle_verified`；它不重发R09，也不构成正式R1或独立第二关口批准。最新结果和证据摘要已追加到第36版续试记录。

本节上述预检状态记载至R17；截至R17，正式PC68-R1尚未启动。其后第37版启动尝试01因输出目录已存在而在请求前停止，结果为 `CASE_NOT_STARTED`，正式请求计数仍为0。`tests/runtime/evidence/issue68-r37-pc68-r1-execution-attempts-20261008.json`（SHA-256 `8109b445f0d97455fbad59cb2a7d5dbc9a0a4636fc98211debe84114abf27a25`）记录尝试编号、未越过请求边界、请求编号未序列化、原始证据摘要及修复方式；原始失败目录别名 `PC68_R37_FORMAL_ATTEMPT01_RAW` 保持不变。下一次仍未发送的唯一正式请求只可在独立审核完成后使用新建空目录 `/private/tmp/pc68-r37-formal-r1-20261008-02`；启动前须确认该路径不存在，启动器创建后为空且与失败目录不相交。该目录不得复用或覆盖启动尝试01的 `/private/tmp/pc68-r37-formal-r1-20261008-01`。请求编号 `issue68-r37-pc68-r1-20261008-01` 尚未写入正式请求，仍只可发送一次。

## 10. 当前交接与完成条件

本次按用户确认沿用共享项目配置入口，不改变验收第四版、实施计划第十三版、两个正式用例及其证明责任。D1继续 `REUSE_PRIOR_PASS`；未变判定代码的合成证据按原版本复用。共享准备程序、正式响应实际生效值记录与 `PASS` 门控已完成。修订前记录的入口测试62项、目录预检测试31项、共享配置助手测试8项、生命周期测试70项、运行配方测试11项、环境预检测试12项及目录接线回归测试11项均通过；生命周期组合本地预检为 `COMBINATION_VERIFIER_READY`，传递位置七场景本地预检为 `PRECHECK_CASES_MATCHED`，证据合同 JSON 解析也通过。安装钩子保证配置助手在 APM 前运行，并在之后核验两个审批值。首轮 Gate 2 修订候选的 R19 判定器70项、生命周期及组合73项通过；其摘要及测试报告见第1节和 `tests/runtime/evidence/issue68-r36-gate2-fix-validation-20261008.json`。第二次修订候选针对前缀输入矩阵与终态优先级新增覆盖，顶层复验142项全部通过；源码摘要、命令及控制台摘要见 `tests/runtime/evidence/issue68-r36-gate2-prefix-matrix-validation-20261008.json`。这些本地测试不代表 Gate 2 已通过。

R09 确认支持安装、配置保留及实际审批值，但未观察到目录标记命令；该次结果仍保留为 `NOT TESTED`，原请求没有重发。R17 使用新消费者和新独占目录重新完成一次无业务预检：APM 0.29.0 在40秒内成功安装10个依赖和1个MCP服务，安装后审批值保持 `on-request` 与 `auto_review`；唯一标记命令创建、读取核对、删除并确认不存在，退出码为0，前后目录快照完整、同根且为空，消费者和评估服务均未改变，结果为 `PASS / single_request_marker_lifecycle_verified`。第17次启动器首次因默认缓存权限受限而在预检脚本启动前停止；新一轮仅为本地启动器使用可写临时缓存，实际标记命令仍使用计划指定的独立缓存。R17只发送一次新请求，不重复R09请求。R15在300秒退出124，短于规定的600秒保护窗口；R11在710.7秒由人工中断；两项执行偏离均保留。R10–R16均未发送评估请求。截至R17，第二关口为 `INCOMPLETE`，正式R1尚未启动；后续正式尝试状态见下文。运行记录及脱敏证据见 `tests/runtime/evidence/issue68-r36-project-approval-config-preflight-continuation-20261008.json`。

第36版复审时的待办是由独立第二关口审核者检查当时的唯一方案、完整源码清单、绑定源码摘要的测试记录、R02–R17安装记录、P01–P03顺序探针、R09原始请求响应、R17新预检请求响应及 PC68-R1 无效尝试摘要和原始证据。R09的 `NOT TESTED` 不得解释成通过，R17预检通过也不构成正式运行许可。R02–R17安装记录及第36版本地完成度复核均是历史材料；它们不代替本版 Gate 2 复审。

第36版 Gate 2 的历史结论如下：首轮为 `NEEDS_MODIFICATION / INCOMPLETE`；候选 `51822296c91a15683e3636f02d5ef5d50b1002e7` 的独立复审于2026-10-08完成，结论为 `NEEDS_MODIFICATION / COMPLETE`，指出精确 `direnv` 前缀下输入矩阵覆盖不足，且缺少有效业务结果与生命周期缺证组合的证明。测试源码提交 `d35d42d5cc3b88014af8eff171f266f93d5051a7` 补齐覆盖，顶层复验142项通过。候选 `a9089032dddeab0a93c19d60b7a8c1f0e72773b6` 的独立第二复审于2026-10-08完成，结论为 `PASS / COMPLETE`；审核覆盖计划、源码摘要、142项验证、执行审查、修订后的 `SKILL.md` 和正式尝试记录。这些结论只适用于第36版，不代表 Gate 3 业务运行结果，也不替代本版新的独立计划审核及 Gate 2。

针对原正式执行的独立实现审查覆盖 `COMPLETE`，总体结论为 `NONCOMPLIANT_PARTIAL`：错误保存外层业务对象、改写日文路径后追加部分分配、漏掉总览调用及未清理传递文件均有事件证据；用户报告的教授最终状态因子代理最终消息不可读而证据不足。审查确认分配与发现代码本身没有静态缺陷，但 `SKILL.md` 修订前只规定总览“最多调用一次”，未要求必须调用，构成静态指令缺口。本轮已修订根调用说明，要求只保存 `choices` 列表、原样使用路径、一次分配全部 owner，并在消费完结果后必须重建总览；审查原文和事件索引见 `tests/runtime/evidence/issue68-r36-implementation-execution-audit-20261008.json`。本次说明修订不改变原正式执行事实，也没有重判或重发正式请求。正式 PC68-R1 于2026-10-08只发送一次，记录 `tests/runtime/evidence/issue68-r36-pc68-r1-execution-retry-20261008.json` 的终态是 `INVALID_TEST_EXECUTION / NOT_DETERMINED`，不是有效 Gate 3 的 `PASS` 或 `FAIL`。原始尝试中，首条分区命令因默认 uv 缓存权限失败；随后改动 `UV_CACHE_DIR`、把夹具目录 `試験` 改为 `试验`，并追加只处理 X owner 的第三次分区调用。这些执行偏离原样保留；旧尝试的 `plan.sha256` 与 `test_revision` 不代表当前候选源码。第31版历史 `PASS / COMPLETE` 只对其原提交有效，不沿用为新运行配置批准。审批未自然发生不是本例阻断；需要权限的步骤未完成时保留未完成事实，不能跳过步骤。

审核者按测试规则第3.3节检查本文与固定测试实现：唯一完整来源、需求对应、最小充分用例、命令和输入、隔离、直接证据、有效成功/有效失败/无法判断三类判定、预检版本及目录对应、终态唯一性和复验来源。完成后才给出独立第二关口结论和冻结版本；本方案不自行授予通过。

本版仅在独立计划审核完成、针对本版的 Gate 2 明确给出 `PASS / COMPLETE`，且第4节预检在全新消费者上确认固定产品 `faab365d0be2bb66f2f285fdaa2927631dbf33f8` 后，授权用唯一新运行编号 `issue68-r37-pc68-r1-20261008-01` 发送一次正式 `PC68-R1` 请求。第37版启动尝试01是请求前失败：详情及原始证据摘要见 `tests/runtime/evidence/issue68-r37-pc68-r1-execution-attempts-20261008.json`（SHA-256 `8109b445f0d97455fbad59cb2a7d5dbc9a0a4636fc98211debe84114abf27a25`），正式请求数为0、请求编号未序列化。保留失败目录 `/private/tmp/pc68-r37-formal-r1-20261008-01` 不变；唯一获准的新请求必须由启动器在此前确认不存在的 `/private/tmp/pc68-r37-formal-r1-20261008-02` 建立空输出目录后发送，不得复用失败目录。第36版无效尝试及其原始证据同样必须保留，不重判、不覆盖。请求一经发送，不重试完整正式请求；六种终态按第5节判定。当前本版独立计划审核和 Gate 2 尚待完成，因此此刻不得启动正式请求。没有本版冻结及有效 Gate 3 结果时，合并仍未就绪。

本地预检复用说明：生命周期组合汇总的 `plan_revision` 为 r26，传递位置汇总为 r27；两组均在本轮本地运行并得到预期场景结果。仅将它们作为未变预检源码所覆盖场景的兼容性回归证据，不称为与 r37 计划编号绑定的结果，也不据此认定第二关口通过。

## 11. 第37版正式执行结果及修复边界

第37版唯一正式 `PC68-R1` 请求已于2026-10-08发送一次，记录见 `tests/runtime/evidence/issue68-r37-pc68-r1-formal-execution-20261008.json`。运行以 `CASE_STARTED / FAIL_PRODUCT / owner_result_path_changed` 结束，合并未就绪。该结果是有效产品失败；不覆盖第36版历史结果，也不因后续代码修复而改判。

正式事件表明：根任务只保存了用户提供的 `choices` 列表，原样保留两位教授的路径，并在一次完整调用中分配全部 owner。两个教授均返回固定预期 `needs_refresh / verify_missing`。失败发生在交接包：两份文件都没有本教授专属的标量 `result`，却都包含完整的 `raw_results_by_professor_dir` 映射，使每位教授输入了兄弟教授的路径。根任务随后只调用一次总览重建；该调用如实返回 `error / missing_email_pack`，但最终答复没有包含完整总览对象。生命周期收集未能归属分区调用的返回值，因为根任务把文件创建和分区命令合并在一次 shell 执行中；它记录了两次读取、两次交接和一次成功清理，最终状态为 `BLOCKED_OBSERVABILITY / transfer_creation_and_cleanup_unobservable`。原始材料保留在本机专用运行目录，仓库只提交脱敏摘要与摘要值。

本轮修正将每个 owner 的结果映射成只含自身路径的标量 `result`，在准备阶段把兄弟结果路径纳入隔离检查，并由验证器拒绝包含全局结果表或多个 owner 的交接包。根提示还要求每条命令单独执行、最终报告完整总览对象，并清理本请求的选择文件、完整分配文件及各 owner 交接文件。回归用例覆盖上述输入隔离和完整回执；223项本地复验结果见 `tests/runtime/evidence/issue68-r37-postfix-local-validation-20261008.json`。该修正只证明当前实现和本地回归；它不能改变已经发生的正式失败，也不等于新的正式运行通过。

本计划授权的正式请求次数已用尽，不得在本计划下重发。任何后续正式请求必须先提出新计划版本，更新输入、执行和生命周期证明，再完成独立计划审核、Gate 2 审核及其规定的准入检查。
