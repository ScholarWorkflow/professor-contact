# 第68号议题测试计划：按最新规则重建

版本：`issue-68-test-plan-r54-2026-10-10`。

目标仓库：`ScholarWorkflow/professor-contact`；拉取请求：[第72号](https://github.com/ScholarWorkflow/professor-contact/pull/72)。正式运行安装拉取请求分支 `codex/issue-68-stage5-per-professor` 的当前版本，安装后立即从锁文件记录实际 `resolved_commit`，并将其冻结为本次产品提交。本文件是第五十四版唯一完整计划，取代第五十三版；不自行授予正式请求执行许可。第五十三版及更早版本的设计审核和第二关口状态仅为历史记录。

第四十三版的预检通过，但申请人资料和模板当时位于运行目录的 `profile/` 下，正式请求以消费者目录为工作目录，二者位置不一致，旧结果不能证明正式请求可读取同一资料。第四十四版已将三份文件移入消费者工作目录，并在该位置重新生成两位教授的第三阶段前置资料、第四阶段本地邮件包，再执行两份第五阶段预检：第三阶段两位均成功，第四阶段总状态和两位教授结果均为 `ok`，第五阶段两份结果均为 `status: ok` 且对应 `verify: ok`。阶段2/3只作本轮输入准备，不作为新增验收项。第四十六版纠正计划编写遗漏：本次执行步骤必须包括测试配置文件及加载方式，详见第4.1节第5项。推送前已发现远端第四十五版在 `fe9a2534505e8e5a78303bb36d970ea8c7eccc7e` 加入配置文件；本版直接引用该已有文件，不重复新建共享配置。2026-10-09，用户确认使用本拉取请求中的该文件作为本轮配置来源；隔离消费者配置接线和保留原配置检查、合成前置资料准备、联系方式证据生成、阶段4邮件包生成及两份阶段5计划预检均已完成，评估服务端口连通检查通过。第四十八版之后的正式请求因命令含 `--ephemeral`，两次原生委派均未建立子任务或产生教授业务结果；第四十九版记录为测试步骤错误导致的无法判断。第五十版补入审核意见要求的真实委派、结果等待与消费、总览先后次序和传递文件清理检查，并更新缺陷隔离修复后的确定性回归记录。第五十一版进一步明确须核验准确的 `agent_type`，以及用调用编号和子任务编号对应委派、完成读取与总览调用顺序。第五十二版撤销把评估服务读取结果解释为根代理内部消费证明的要求，但仍错误地把只含元数据的 `output.child_thread_reads` 当成两份子任务业务结果来源。第五十三版把该字段限制为核对子任务身份和父子关系，业务结果改由教授本地业务产物、总览内容和最终回复交叉检查。第五十四版改为在执行时安装目标分支当前版本并记录实际产品提交，同时更正正式规则来源；业务目标、检查方式、正式请求次数和停止条件不变。第五十四版计划设计已通过，第二关口待复核，替代正式请求仍须取得明确授权。

## 1. 正式依据与范围

- [当前需求](https://github.com/ScholarWorkflow/professor-contact/issues/68)：第五阶段按教授独立处理；一位教授失败不影响另一位教授的合法结果。
- [验收第四版](https://github.com/ScholarWorkflow/professor-contact/issues/68#issuecomment-5981562292)：`R68-1`至`R68-8`、`AD68-1`至`AD68-5`；沿用已确认业务目标。
- [产品执行计划第十三版](https://github.com/ScholarWorkflow/professor-contact/issues/68#issuecomment-6000673923)及[保留批准的审核](https://github.com/ScholarWorkflow/professor-contact/pull/72#issuecomment-6008709709)：用于理解产品负责者及当前文件接口，不新增验收目标。
- 计划沿用已确认的验收范围，并以任务工作区指定的 `Test Engineer Rule.md` 与 `PROJECT_CONSENSUS.md` 为正式测试和操作规则；计划设计复核另适用 `Plan Reviewer Rule.md`。目标仓库不复制这些规则文件，也不以旧计划或审核意见替代当前规则。
- 用户本轮明确要求删除旧方案后按最新规则重建，允许精简重复检查，无须证明旧方案存在缺陷。

姓名不同的教授可以使用相同邮件编号，身份仍由教授规范目录与邮件编号共同确定。假定教授姓名唯一，不测试同名教授，不要求同名支持或拒绝。前四阶段、历史迁移、通用写锁、邮件文案质量和无关运行环境不属于本轮测试。第67号、第48号议题不是本轮新增测试或合并前置。

下表是本轮必测清单及验收上限。每项仅列目标、输入或场景、预期结果及检查方式。确定性程序由既有测试结果检查；一次实际代理运行同时检查正常业务结果、两次准确委派、两个正式子任务、总览结果和传递文件清理。根代理是否使用两位教授的结果，由最终回复与教授本地业务产物及总览返回的一致性判断，不另设内部读取事件或完整调用链证明。只读取该次响应已有的事件、子任务关系元数据和业务产物，不新增采集器或读取子代理真实提示词。

## 2. 必测清单

| 项目与业务目标 | 输入或场景 | 预期结果 | 检查方式 |
| --- | --- | --- | --- |
| 甲：本地输入是唯一事实来源，禁止旧全局回退；`R68-1、R68-6` | 教授本地包有效、缺失或与旧全局包不同 | 只使用显式本地包；本地包缺失时拒绝；旧全局包不改变结果，不新增迁移或双写 | 复用历史确定性检查 `P1` 的断言与结果；本轮不重跑 |
| 乙：指定单邮件的兼容与自身校验；`R68-2` | 只选择当前教授一封邮件，同时含未选中邮件；另有目标自身缺失、重复、字段、收件人或跟进日期错误 | 未选中邮件不阻断目标；目标自身错误仍拒绝；只更新目标输出 | 复用 `P2` 及 `P7` 中目标选择范围和业务校验的既有断言；不穷举新组合 |
| 丙：同教授整批提交；`R68-3` | 不指定邮件编号；当前教授多封邮件全部有效，或其中一封尚不满足提交条件 | 全部有效时提交当前教授全部邮件；一封不满足条件时不先提交另一封，不自动拆成逐邮件事务 | 复用 `P3` 的批量正常路径与失败不写入断言 |
| 丁：教授之间及校验状态相互隔离；`R68-4、R68-7、R68-8` | 教授甲有效，教授乙输入、选择或本次输出有错误；校验只针对当前教授输出 | 甲的合法提交保持，乙错误只属于乙；不读取或写入另一位教授的业务状态来决定当前结果 | 复用 `P4`、`P2` 中教授隔离和本地校验断言；当前实际代理正常输出归属由辛检查 |
| 戊：总览独立派生与人工修改保护；`R68-5、AD68-2` | 教授本地结果完成后重建总览；总览不存在、输入损坏或存在人工修改 | 从各教授最后本地状态派生；可重建；损坏或人工冲突时保留旧总览，单独报告，不回滚教授提交 | 复用 `P5` 的总览正常重建、保护及独立性断言；根代理报告由辛检查 |
| 己：独立启动只读发现；`AD68-3` | 同项目含有效教授本地包及损坏包 | 有效包仍可选，坏包只报告所属教授问题；发现不修改业务文件，不将全局包或其他业务状态当作来源 | 复用 `P6` 中只读发现、逐教授返回与坏包隔离断言 |
| 庚：确定性选择分配与原值保持；`AD68-4、AD68-5` | 显式教授目录选择、无目录唯一候选或真实歧义、姓名不同但邮件编号相同、目标邮件及整教授选择 | 按目录与编号确定归属；歧义不广播；目标外行先过滤；一位教授分配失败不阻断另一位；行值和路径不被翻译或重建 | 复用 `P7` 中已确认范围的分配断言；不复用同名场景作为要求，也不检查全部内部步骤 |
| 辛：修复后的实际代理能完成各教授自己的业务；`R68-4、R68-8、AD68-1、AD68-5` | 两位姓名不同的教授，各有合法本地包、已满足的核验条件、完整选择及内容可区别的合法结果文件。按普通第五阶段请求处理两位教授，不预设提前停止 | 两位教授分别完成本次指定邮件；根代理分别委派并使用两位教授的结果；每位代理使用本教授数据，不串用；最多重建一次包含两位教授本次结果的总览；完成后清理本次传递文件。最终回复准确区分教授业务与总览结果 | 运行一次普通请求；从该次响应已有的应用服务事件核对两次准确委派及一次总览调用，用 `output.child_thread_reads` 只对应两个正式子任务的身份和父子关系。检查两位教授邮件文件及本地状态分别与各自固定输入一致，总览返回及文件包含两位教授本次结果，本次传递文件已清理；按第3.3节将最终回复与业务产物及总览返回对照。不从子任务读取元数据推断业务正文或根代理内部读取，不读取真实提示词，不增加独立采集器或新的业务场景 |

辛保留一次实际运行的理由：本次修改包含根代理和教授代理的调用说明，旧正常提交结果只覆盖确定性程序，第三十七版实际运行停在核验未完成，未使用指定结果文件。需要观察修复后的正常请求能否产出各自正确的业务文件，并确认两次准确委派、两个正式子任务、包含两位教授本次结果的总览、清理及最终汇报。检查均在同一次普通请求中完成，不证明根代理内部读取过程，不重测邮件渲染、校验及提交算法的所有分支，也不新增失败组合。

根代理写出的交接文件不等于子代理实际收到或使用的内容；子任务关系元数据也不包含子任务业务正文。本计划只用 `output.child_thread_reads` 对应两个正式子任务的编号、父任务、关系类型、读取请求、任务元数据和错误；教授身份及业务完成情况由准确委派、各教授本地业务产物和固定输入核对，再以最终回复和总览返回是否准确反映两位教授的业务结果判断根代理的可观察业务使用情况。不把该字段解释为业务结果或根代理内部读取证明，不要求取得不可见的真实提示词，也不保存完整路径传递过程。仅出现其他教授的路径不能单独判为业务串用；本次输出错归属、错内容或所需输入无法使用，才按实际业务事实判定。业务产物正确只能支持本次业务结果，不能证明所有内部步骤。

单教授请求沿用同一委派、使用结果与总览顺序。本轮不新增单教授实际运行：确定性单教授业务已有乙、丙覆盖，单教授与多教授共用的调用说明由本地测试工程师在步骤接线时核对；如当前产品出现单教授专属的行为修改，再按实际影响修订对应项目。

## 3. 既有结果与复验范围

### 3.1 确定性业务结果直接复用

甲至庚的既有结果来源于仓库内保留的[历史确定性结果](../.apm/skills/professor-contact/tests/runtime/evidence/issue68-d1-r29-history.json)。记录的产品提交为 `35f2785b4d13783683860db910a36add2347bd29`，测试代码提交为 `e931ab22fbe492bdf0c4ecb74e906d2c23dfce23`，七组检查均通过，合计43个不同测试组件。这是历史版本的证据，不作为 `72f20846` 新增教授本地阶段4邮件包及其阶段5交接行为的验证，也不把43个组件设为本轮重建或重跑门槛。

此前计划写有“五模块128项通过”，但原始报告无法找到；2026-10-09 的复跑实际为128项中2项失败，失败源于 T59 缺陷子项复用共享临时状态。2026-10-10 已将该测试改为每个缺陷子项各自创建完整初始根目录，并重新运行 `test_contact_state`、`test_stage4_selection_agent_contract`、`test_stage5_dualtarget_contract`、`test_stage5_immutable`、`test_issue67_gate2_r3`：128项全部通过，退出码为0。另运行请求构建器的 `test_issue68_eval_request`，6项全部通过，包含准确参数不含 `--ephemeral` 的断言。完整命令、隔离修改和仓库外日志见[本地回归记录](issue68-test-execution-2026-10-09.md)。这些确定性结果不证明模型生成的实际业务文件正确；辛仍保留一次正式正常路径运行。

甲至庚继续沿用历史结果中仍适用的断言；新增的教授本地阶段4交易与邮件包交接由上述当前提交的针对性回归覆盖。后续代理和技能说明修复影响辛，不恢复用户删除的测试代码，不因提交编号变化重跑既有历史结果，也不新增判定程序。

历史记录中的其他场景不进入本轮清单；43项不是必须重建或重跑的数量。需要核对结果时，用 `jq` 读取 `execution.producer.sha`、`final_verdict.verdict` 及 `proofs[]` 中对应组的结果；采用原标准测试报告，不重新认证其生成过程。

### 3.2 保留正式失败，只复验实际受影响项

保留[第三十七版正式运行记录](../.apm/skills/professor-contact/tests/runtime/evidence/issue68-r37-pc68-r1-formal-execution-20261008.json)及[原审核](https://github.com/ScholarWorkflow/professor-contact/pull/72#issuecomment-6064307703)。原结论为交接结果路径问题，原记录不改写、不重判为当前通过；它不证明教授实际错用了别人的文件，因为当时尚未走到结果文件消费与邮件提交。

同次记录已观察到只保存用户选择列表、保留发现路径、一次完整分配、两位教授如实返回核验未完成、一次总览调用及请求文件已经删除。这些事实保持原范围，可直接复用，不能说成该次整个运行通过。旧专用程序无法还原创建与分配的中间过程，记为原观察受阻；最新规则不要求重建这个过程。清理采用实际文件状态，不因旧观察程序受阻自动重跑。

本轮已取得原运行保存的响应，按 `output.events[]` 的 `item.completed / agent_message` 类型读取根代理最后回复。该回复明确报告两位教授分别为 `needs_refresh / verify_missing`，总览为 `error / missing_email_pack`，并说明总览错误未改变教授结果。与保留的接口结果相符。“未包含完整总览对象”不是汇报错误，第三十九版把它当成业务失败依据的表述在本版纠正。原始响应继续留在原运行目录，不上传；历史失败及观察受阻记录仍保留原归属。

第三十七版的生命周期结论受可观察性问题影响，不能证明当前版本的两次准确委派、两个正式子任务、两位教授正常完成的业务产物、包含两位教授本次结果的总览或传递文件清理。第五十四版继续在一次替代正式请求中按现有响应事件、子任务关系元数据、业务产物、总览内容、最终回复和文件状态检查这些验收项；不增加另一轮运行，不证明根代理内部读取过程，不重测发现与分配算法的既有分支。

### 3.3 如何检查接口结果与最终回复

总览文件由 `contact_state.py stage5-rebuild-overview` 根据本地状态生成，根代理负责调用和说明结果；不把代理最终回复当作总览文件。生成算法、失败不覆盖和人工修改保护的结果复用戊，不在辛重测这些分支。

检查员从同一响应的 `output.app_server_events` 核对准确代理名的两次委派请求及其成功返回，并确认 `stage5-rebuild-overview` 最多调用一次；从 `output.child_thread_reads` 按子任务编号核对两个正式子任务的编号、父任务、关系类型、读取请求、任务元数据和错误。该字段不含任务轮次，不用于取得业务正文、识别教授业务归属或证明根代理内部读取。教授身份由两次委派的任务名称等非提示词字段、本地教授目录和固定输入对应；业务完成情况由两位教授各自的邮件文件及本地状态核对。随后检查总览返回和总览文件包含两位教授本次完成的结果，再将根代理最终回复与教授业务产物及总览返回对照。这里以总览确实包含两位教授本次结果作为结果完成后生成总览的业务观察点，不比较 `child_thread_reads` 或 `output.events` 中不存在的 `runtime_seq`。响应字段若不能对应委派和正式子任务，业务产物不能对应固定输入，或总览内容不能确认包含本次两份结果，相关项记为无法判断。JSON 用 `jq` 解析；只读取当前目标涉及的字段，不要求新采集程序或另存完整调用链。具体输出路径由本地测试工程师在第4节补齐。

| 对照对象 | 通过标准 | 业务失败的具体情况 |
| --- | --- | --- |
| 两位教授的归属与业务产物 | 各教授实际文件及状态对应准备时固定的本教授目录、目标邮件编号和可区别的结果内容；回复能分清各自结果，声称完成时有相应产物 | 用了另一位教授的内容、写到另一位目录、输出缺失却宣称完成，或把一位教授的问题错误算到另一位 |
| 教授未完成或失败的实际结果 | 若返回缺输入、需刷新、失败或部分完成，回复如实说明所属教授及实际问题，不说全部完成 | 将未完成说成成功，漏掉一个实际未完成的教授却称本次全部完成，或捏造失败原因 |
| 总览返回 `status: ok` | 回复说明总览已生成；给出位置时与 `overview_md` 对应，总览文件实际存在 | 宣称生成但无实际文件，或给出错误文件位置 |
| 总览返回 `status: needs_decision` | 回复说明总览未更新、需要处理人工修改冲突；教授结果单独保持 | 宣称已更新，或把该冲突说成已成功教授业务的失败 |
| 总览返回 `status: error` | 回复说明总览未生成或未更新及实际原因，教授结果单独保持 | 把总览失败说成成功，或因它把已成功教授结果改称失败 |

上表定义遇到相应返回时如何判断，不要求为每一行新增运行或故障注入。辛预期为正常完成；若实际教授未完成，按业务返回说明原因并将正常业务目标记为失败或无法判断，不能因最终回复说得准确就把辛整体判通过。环境或观察问题导致无法判断时，保留这个区别，不冒充产品失败。

最终回复允许自然语言概括原因，不要求逐字复制 JSON、原因码或完整对象，不要求固定模板。某一事实没有被报告且影响用户判断是否完成、哪位教授有问题或总览能否使用，才是漏报；措辞不同不构成失败。现有结果或回复确实取不到时标为无法判断，不推测内部提示词、等待过程或返回内容。

## 4. 执行步骤

本节记录辛的一次替代正式运行步骤。第四十三版的申请人资料和模板位于消费者工作目录外；第四十四版已在消费者工作目录内重新生成合成前置资料及教授本地邮件包，并完成两份阶段5预检，均达到计划所列状态。2026-10-09，用户确认复用本拉取请求中的测试配置文件；本地测试工程师已在隔离消费者完成配置接线、合成资料准备、阶段4邮件包生成及两份阶段5计划预检。第四十八版之后发送的正式请求使用了含 `--ephemeral` 的构建器；评估服务接收并完成根任务，但两次原生委派均未建立子任务或产生教授业务结果，详见[正式运行记录](issue68-test-execution-2026-10-09.md)。该次结果属于测试步骤错误导致的无法判断，不计作辛的业务失败或通过。第五十四版计划设计已通过，第二关口待复核；执行者必须等待第二关口通过并取得明确请求授权，才能发送一次替代正式业务请求。不得调用已删除的第三十八版及更早运行器，也不得从旧评论拼接执行命令。

### 4.1 消费者与版本

1. 目标产品来源固定为第72号拉取请求分支 `codex/issue-68-stage5-per-professor`。正式安装只解析该分支一次；安装完成后，从消费者锁文件取得实际 `resolved_commit`，保存为 `PC68_PRODUCT_SHA`，本次准备、正式请求和结果全部归属于该提交。分支此后继续变化不改变已经安装的消费者；需要判断新提交时只分析受影响目标，不自动废除未受影响结果。
2. 在仓库及其工作树之外创建唯一运行目录并设置变量：`PC68_RUN_ROOT="$(mktemp -d /private/tmp/pc68-r44-20261009-XXXXXX)"`、`PC68_CONSUMER="$PC68_RUN_ROOT/consumer"`、`PC68_PROGRAM="$PC68_CONSUMER/testdata/program"`、`PC68_PROFILE="$PC68_CONSUMER/套磁邮件/套磁信息.md"`、`PC68_TEMPLATE="$PC68_CONSUMER/套磁邮件/套磁模板.md"`、`PC68_FOLLOWUP_TEMPLATE="$PC68_CONSUMER/套磁邮件/套磁跟进模板.md"`、`PC68_SCRIPT="$PC68_CONSUMER/.agents/skills/professor-contact/scripts/contact_state.py"`、`PC68_CONTACT_TESTS="$PC68_CONSUMER/.agents/skills/professor-contact/tests"`、`PC68_CONTACT_EVIDENCE_SCRIPT="$PC68_CONSUMER/apm_modules/ScholarWorkflow/professor-research/.apm/skills/professor-collector/scripts/contact_evidence.py"`。设置 `UV_CACHE_DIR="$PC68_RUN_ROOT/uv-cache"` 并导出。创建空消费者、程序目录及各输入文件的父目录；申请人、研究资料和模板只使用本计划所列合成内容。申请人资料和两份模板均置于 `$PC68_CONSUMER/套磁邮件/`，即正式请求的 `--cd "$PC68_CONSUMER"` 工作目录下；预检显式传入这些变量，正式请求按产品约定从调用方工作目录读取同一文件。`request.json`、`response.json`、`selection-input.json` 位于运行目录。不得复用 R37 的原始运行目录，不得在产品仓库内放置临时输入或输出。
3. 在空的 `$PC68_RUN_ROOT/consumer` 中通过正式安装入口创建消费者：运行 `apm init -y --target codex`，然后运行 `apm install https://github.com/ScholarWorkflow/professor-contact.git#codex/issue-68-stage5-per-professor --target codex --trust-transitive-mcp`。保存安装命令与退出码到运行目录。安装后只用消费者锁文件确定本次实际产品提交，并用 `yq` 检查字段：

   ```sh
   yq -e '.dependencies[] | select(.name == "professor-contact") | .resolved_commit | test("^[0-9a-f]{40}$")' "$PC68_CONSUMER/apm.lock.yaml"
   PC68_PRODUCT_SHA="$(yq -r '.dependencies[] | select(.name == "professor-contact") | .resolved_commit' "$PC68_CONSUMER/apm.lock.yaml")"
   printf '%s\n' "$PC68_PRODUCT_SHA" > "$PC68_RUN_ROOT/product-sha.txt"
   yq -e '.dependencies[] | select(.name == "professor-research") | .resolved_commit == "a9e7ffbc070dcfdc7b225e5e70de1b4576649ecd"' "$PC68_CONSUMER/apm.lock.yaml"
   ```

   `PC68_PRODUCT_SHA` 必须是锁文件中实际解析出的40位提交编号；记录后不得在本次运行中重新安装或再次解析分支。`professor-research` 依赖仍须为 `a9e7ffbc070dcfdc7b225e5e70de1b4576649ecd`。历史安装曾遇到 HTTPS 连接中断并按原命令重试成功；本次若再次发生，按第4.4节的停止与重试规定处理并保留命令、退出码及日志。禁止使用本地路径、符号链接、手工复制或修补安装产物。
4. 使用现有评估服务作为请求入口，不启停或重启服务。本次测试配置文件与加载步骤见下一项，服务自身配置不作为本次修改对象。在已配置的 `eval-server` 仓库工作目录执行 `direnv exec . sh -c 'printf "%s\\n" "$EVAL_PORT"'` 取得端口；不得在计划、请求或提交中写入端口、个人绝对路径、密钥或服务进程信息。
5. **测试配置文件属于本计划的执行步骤**。本次模型和推理设置直接引用远端已提交的 [测试配置文件](issue68-eval-codex-config.toml)，文件版本为 `issue-68-eval-codex-config-r1-2026-10-09`，来源提交为 `fe9a2534505e8e5a78303bb36d970ea8c7eccc7e`。两项设置固定为：

   ```toml
   model = "gpt-6-luna"
   model_reasoning_effort = "low"
   ```

   **正式请求发送前的准备记录：配置接线和本地预检已完成**。2026-10-09，用户确认复用本拉取请求中已有的版本化文件。隔离消费者已通过正式安装入口创建，锁定版本符合第3项；安装生成的 `.codex/config.toml` 保留了原有条目，仅增加 `model = "gpt-6-luna"` 与 `model_reasoning_effort = "low"`。按 TOML 解析后逐项比较，其他配置键和值保持一致。正式安装只使用固定 GitHub 提交，没有手工复制或修改安装产物。合成前置资料、联系方式证据、阶段4邮件包和阶段5计划预检均已按本节执行并通过；端口连通检查也已通过。此段仅记录当时尚未通过正式请求实测评估服务加载项目配置的历史状态；当前请求状态以第4.4节及第6节第四十九版修订记录为准。执行者不寻找评估服务配置，不改服务启动配置或用户默认配置，不新增配置认证请求。

   配置来源决定：2026-10-09，用户确认使用本拉取请求 `plan/issue68-eval-codex-config.toml`，版本为 `issue-68-eval-codex-config-r1-2026-10-09`、来源提交为 `fe9a2534505e8e5a78303bb36d970ea8c7eccc7e`。保留并直接复用该文件，不另建共享文件，不新增业务测试。

   在包含上述提交的本测试计划仓库根运行 `pwd`，以返回路径设置 `PC68_RECIPE_ROOT`，再设置 `PC68_TEST_CONFIG_SOURCE="$PC68_RECIPE_ROOT/plan/issue68-eval-codex-config.toml"` 和 `PC68_TEST_CONFIG="$PC68_CONSUMER/.codex/config.toml"`。引用的是本次配套测试文件，不是消费者安装产物或个人默认配置。消费者已有正式安装生成的配置，不整份覆盖其中的代理、工具或其他安装内容；用现有 `yq` 仅合入两项模型设置，中间文件放运行目录：

   ```sh
   test -r "$PC68_TEST_CONFIG_SOURCE" && test -r "$PC68_TEST_CONFIG"
   yq -p toml -e '.model == "gpt-6-luna" and .model_reasoning_effort == "low"' "$PC68_TEST_CONFIG_SOURCE"
   yq eval-all -p toml -o toml '. as $item ireduce ({}; . * $item)' "$PC68_TEST_CONFIG" "$PC68_TEST_CONFIG_SOURCE" > "$PC68_RUN_ROOT/test-config-merged.toml"
   yq -p toml -e '.model == "gpt-6-luna" and .model_reasoning_effort == "low"' "$PC68_RUN_ROOT/test-config-merged.toml"
   cp "$PC68_RUN_ROOT/test-config-merged.toml" "$PC68_TEST_CONFIG"
   ```

   以上只准备隔离测试消费者的运行参数，不修改安装生成的代理、技能或工具启动定义。项目配置需要项目受信任才能加载，沿用共享测试资产 `docs/codex-opencode-smoke-wiring.md` 的已有仅授予项目信任的入口：第4.3节请求传入 `projects={...trust_level="trusted"...}`，只对本次隔离消费者生效。模型和推理强度仍从上述文件加载，不在请求参数重复覆盖。这条信任接线是配置加载前提，不是新增验收目标；不重做既有信任检查。

   加载依据：[官方配置说明](https://developers.openai.com/codex/config-basic)：通过请求的工作目录加载受信任项目的 `.codex/config.toml`。现有评估服务命令映射已支持 `--config` 的项目信任参数；参考 `RekiDunois/eval-server@3fdfa9387140cfc2e2aa3af415f85015f79706d2` 的 `codex_appserver/commands.py`。本计划只引用该已有入口，不要求重新认证服务本身。上述配套文件缺失、合入失败或既有加载前提不成立时，停止并交本地测试工程师补准备，不能记作产品失败。


### 4.2 合成业务输入

1. 在 `$PC68_RUN_ROOT/consumer/testdata/program/教授研究/` 准备两位虚构教授：`山田太郎` 与 `佐藤花子`，分别位于 `工学/山田太郎/` 和 `社会情報/佐藤花子/`。各教授只准备一封邮件；两位教授的方向及想法编号均为 `DIR00001/DIR00001_1`，邮件编号分别为 `山田太郎::DIR00001::DIR00001_1`、`佐藤花子::DIR00001::DIR00001_1`。身份由教授目录与邮件编号共同确定。研究材料必须明显不同：前者围绕地域交通需求变化，后者围绕沿岸灾害信息共享；不写入真实个人或学校资料。
2. **合成前置资料来源及生成步骤：**阶段2/3仅用于构造本轮双教授输入，不作为新增验收项，也不发送阶段2/3代理请求。使用固定提交消费者内已有的 `$PC68_CONTACT_TESTS/test_contact_state.py::BaseEnv.stage3_run`；它通过同目录 `stage2_upstream_fixture.py::prepare_stage2_proof` 生成合法的阶段2前置证明，再以当前安装的 `$PC68_SCRIPT` 运行阶段2完成和阶段3候选完成。按以下过程创建合成申请人、项目信息和模板：

   ```sh
   mkdir -p "$PC68_PROGRAM" "$(dirname "$PC68_PROFILE")"
   jq -n '{university:"合成测试大学",department:"合成信息研究科",target:{intake_year:2027,intake_term:"april"}}' > "$PC68_PROGRAM/info.json"
   jq -n '{exam_type:{degree:"博士前期課程",selection_name:"春季 合成选拔 合成信息专攻"}}' > "$PC68_PROGRAM/boshu_analysis.json"
   cat > "$PC68_PROFILE" <<'EOF'
   申请人：合成申请者
   研究兴趣：面向公共服务的可靠信息处理。
   经验：使用可复现的数据分析方法。
   EOF
   cat > "$PC68_TEMPLATE" <<'EOF'
   {{大学}}／{{研究科}}／{{先生名}}先生
   {{出身校}} {{氏名}}
   {{入学年度}} {{入学月}} {{専攻}} {{学位}}
   {{兴趣段}}
   {{未来志向}}
   {{学習中}}
   {{志望}}
   EOF
   cat > "$PC68_FOLLOWUP_TEMPLATE" <<'EOF'
   {{先生名}}先生
   {{大学}} {{研究科}} {{学位}}
   {{出身校}} {{氏名}}
   {{初回送信日}}
   {{研究主题}}
   {{メールアドレス}}
   EOF
   ```

   把以下代码保存为 `$PC68_RUN_ROOT/prepare-stage3.py`，再用 `uv run --offline --no-project python "$PC68_RUN_ROOT/prepare-stage3.py" "$PC68_CONTACT_TESTS" "$PC68_SCRIPT" "$PC68_PROGRAM" "$PC68_PROFILE"` 执行。脚本只在唯一消费者和临时测试目录写入合成资料；每位教授分别调用已有夹具方法，返回状态不是 `ok` 时立即停止：

   ```python
   import json, shutil, sys
   from pathlib import Path

   tests, script, program, profile = map(Path, sys.argv[1:5])
   sys.path.insert(0, str(tests))
   import test_contact_state as fixture
   fixture.SCRIPT = script

   scenarios = [
       ("山田太郎", "工学", "地域交通需求变化",
        "Future work will adapt regional transit planning to changing local travel demand.",
        "Synthetic regional transit demand adaptation",
        "A synthetic study of changing regional travel demand."),
       ("佐藤花子", "社会情報", "沿岸灾害信息共享",
        "Future work will improve information sharing during coastal disaster response.",
        "Synthetic coastal disaster information sharing",
        "A synthetic study of information sharing for coastal disaster response."),
   ]
   for name, field, topic, quote, paper_title, paper_abstract in scenarios:
       env = fixture.BaseEnv("runTest")
       env.setUp()
       try:
           original_dir = env.prof_dir
           env.root = program
           env.prof_dir = program / "教授研究" / field / name
           env.prof_dir.mkdir(parents=True, exist_ok=True)
           shutil.copytree(original_dir / "论文分析", env.prof_dir / "论文分析", dirs_exist_ok=True)
           env.gap_quotes = {"AAAA1111": quote, "BBBB2222": "A second synthetic line of work remains open."}
           for paper in env.papers:
               key = paper["item_key"]
               if key not in env.gap_quotes:
                   continue
               old = Path(paper["analysis_file"])
               analysis = env.prof_dir / "论文分析" / old.name
               sidecar = json.loads(Path(paper["sidecar_file"]).read_text(encoding="utf-8"))
               sidecar["analysis"] = str(analysis)
               sidecar["items"][0]["quote"] = env.gap_quotes[key]
               sidecar["items"][0]["id"] = fixture.quote_id(env.gap_quotes[key])
               Path(str(analysis) + ".future_work.json").write_text(
                   json.dumps(sidecar, ensure_ascii=False), encoding="utf-8")
               paper["analysis_file"] = str(analysis)
               paper["sidecar_file"] = str(analysis) + ".future_work.json"
               if key in ("AAAA1111", "BBBB2222"):
                   paper["title"] = paper_title
                   paper["abstract"] = paper_abstract
           write_facts = env.write_facts
           def write_professor_facts():
               path = write_facts()
               data = json.loads(path.read_text(encoding="utf-8"))
               data["professor"] = name
               data["directions"][0]["name_ja"] = topic
               data["directions"][0]["name_zh"] = topic
               data["directions"][0]["user_note"] = "合成材料仅用于本地准备。"
               data["papers"] = env.papers
               path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
               return path
           env.write_facts = write_professor_facts
           def customize(candidate):
               candidate["title"] = topic
               candidate["one_liner"] = f"以合成资料讨论{topic}。"
               candidate["research_question"] = f"如何用合成资料研究{topic}？"
               candidate["points"] = [f"围绕{topic}构造本地测试内容。"]
               candidate["fit_note"] = "只描述合成材料，不对应真实机构或个人。"
               candidate["why_recommended"] = "与本次合成选择一致。"
           result = env.stage3_run(profile=str(profile), candidate_extra=customize)
           if result.get("status") != "ok":
               raise SystemExit(f"{name} 的阶段3前置资料未生成：{result}")
       finally:
           env.tearDown()
   ```

   该来源和命令已在本计划固定提交的消费者中执行成功；它只产生阶段2/3合成输入，不改变甲至辛的必测清单。
3. 设置 `PC68_YAMADA_DIR="$PC68_PROGRAM/教授研究/工学/山田太郎"`、`PC68_SATO_DIR="$PC68_PROGRAM/教授研究/社会情報/佐藤花子"`。阶段3候选生成后，在各自 `papers.json` 中追加一条当前年份前一年的合成论文：山田使用 `CE-YAMADA`、`10.1/ce-yamada`、`Taro Yamada`；佐藤使用 `CE-SATO`、`10.1/ce-sato`、`Hanako Sato`。例如山田执行 `jq --arg romaji "Taro Yamada" --arg key "CE-YAMADA" --arg doi "10.1/ce-yamada" '.professor.name_romaji=$romaji | .papers += [{item_key:$key,year:2025,doi:$doi}]' "$PC68_YAMADA_DIR/papers.json" > "$PC68_RUN_ROOT/yamada-papers.json" && mv "$PC68_RUN_ROOT/yamada-papers.json" "$PC68_YAMADA_DIR/papers.json"`；佐藤以 `PC68_SATO_DIR`、`Hanako Sato`、`CE-SATO`、`10.1/ce-sato` 执行同一命令。

   在 `$PC68_PROGRAM/教授研究/` 下按以下合成来源写入 `_professor_candidates.json`、`_corresp_cache.json` 和 `_署名对照.json`：两位教授的官方候选邮箱分别是 `taro@example.edu`、`hanako@example.edu`，来源分别为 `https://example.test/faculty/ce-yamada`、`https://example.test/faculty/ce-sato`；`_corresp_cache.json` 的键分别为 `CE-YAMADA`、`CE-SATO`，每条记录的 `paper_year` 为 `2025`、`confidence` 为 `high`、`channel` 为 `correspondence`，`contacts` 中同名联系人使用同一邮箱、`confidence: high`、`channel: pdf_footnote`，`names` 与 `emails` 也各自只含对应教授和邮箱。使用以下 `jq` 命令生成这些输入：

   ```sh
   jq -n '[{name:"山田太郎",name_romaji:"Taro Yamada",email:"taro@example.edu",source:"https://example.test/faculty/ce-yamada",provenance:"合成测试教师资料"},{name:"佐藤花子",name_romaji:"Hanako Sato",email:"hanako@example.edu",source:"https://example.test/faculty/ce-sato",provenance:"合成测试教师资料"}]' > "$PC68_PROGRAM/教授研究/_professor_candidates.json"
   jq -n '{"CE-YAMADA":{itemKey:"CE-YAMADA",paper_year:2025,doi:"10.1/ce-yamada",channel:"correspondence",confidence:"high",contacts:[{name:"山田太郎",email:"taro@example.edu",confidence:"high",channel:"pdf_footnote"}],names:["山田太郎"],emails:["taro@example.edu"]},"CE-SATO":{itemKey:"CE-SATO",paper_year:2025,doi:"10.1/ce-sato",channel:"correspondence",confidence:"high",contacts:[{name:"佐藤花子",email:"hanako@example.edu",confidence:"high",channel:"pdf_footnote"}],names:["佐藤花子"],emails:["hanako@example.edu"]}}' > "$PC68_PROGRAM/教授研究/_corresp_cache.json"
   jq -n '{professors:{}}' > "$PC68_PROGRAM/教授研究/_署名对照.json"
   ```

   `_署名对照.json` 必须保持 `{"professors":{}}`。按该来源调用上游 `professor-research` 的联系方式证据程序：

   ```sh
   uv run --offline --no-project python "$PC68_CONTACT_EVIDENCE_SCRIPT" "$PC68_PROGRAM"
   uv run --offline --no-project python "$PC68_CONTACT_EVIDENCE_SCRIPT" "$PC68_PROGRAM" --check > "$PC68_RUN_ROOT/contact-evidence-check.json"
   jq -e '.result == "fresh" and .artifact_degraded == false and .reasons == [] and (.professors | length == 2) and all(.professors[]; .result == "fresh" and .reasons == [])' "$PC68_RUN_ROOT/contact-evidence-check.json"
   jq -e '(.degraded == false) and (.global_degraded == false) and (.source_errors | length == 0) and (any(.professors[]; .professor.name == "山田太郎" and .verdict == "confirmed_cross_source" and .current_email == "taro@example.edu" and .evidence_status.current_email_blocked_by == [])) and (any(.professors[]; .professor.name == "佐藤花子" and .verdict == "confirmed_cross_source" and .current_email == "hanako@example.edu" and .evidence_status.current_email_blocked_by == []))' "$PC68_PROGRAM/教授研究/_联系方式证据.json"
   ```

   检查程序返回 `fresh`，两位教授均为 `confirmed_cross_source` 且 `current_email_blocked_by` 为空。把选择输入文件 `$PC68_RUN_ROOT/selection-input.json` 写在运行目录；方向编号同为 `DIR00001`、想法编号同为 `DIR00001_1`，但每行均带正确教授目录：

   ```sh
   jq -n --arg root "$PC68_PROGRAM" '{selections:[{professor:"山田太郎",professor_dir:($root+"/教授研究/工学/山田太郎"),direction_ids:["DIR00001"],ideas:[{id:"DIR00001_1"}]},{professor:"佐藤花子",professor_dir:($root+"/教授研究/社会情報/佐藤花子"),direction_ids:["DIR00001"],ideas:[{id:"DIR00001_1"}]}]}' > "$PC68_RUN_ROOT/selection-input.json"
   ```

   每位教授目录只保留其阶段3生成的 `套磁候选输入.json` 和 `套磁候选状态.json`，不手工复制或修改这些文件。
4. **阶段4教授本地邮件包：**按本版新路径运行以下产品入口生成两位教授各自的本地邮件包；禁止复制程序级邮件包或手工改写教授本地包：

   ```sh
   uv run --offline --no-project python "$PC68_SCRIPT" stage4-finalize --program-root "$PC68_PROGRAM" --selection-input "$PC68_RUN_ROOT/selection-input.json" --profile "$PC68_PROFILE" > "$PC68_RUN_ROOT/stage4-result.json"
   jq -e '.status == "ok" and (.results | length == 2) and all(.results[]; .status == "ok")' "$PC68_RUN_ROOT/stage4-result.json"
   ```

   用以下命令核对两份包的版本、所有者、唯一邮件编号和邮箱证据；不得把一个教授的包写入或作为另一教授的输入：

   ```sh
   jq -e --arg dir "$PC68_YAMADA_DIR" '.schema == 3 and .kind == "professor-contact-email-input" and .professor == "山田太郎" and .professor_dir == $dir and (.emails | length == 1) and .emails[0].email_id == "山田太郎::DIR00001::DIR00001_1" and .emails[0].contact_evidence.record.verdict == "confirmed_cross_source" and .emails[0].contact_evidence.record.current_email == "taro@example.edu" and .emails[0].contact_evidence.record.evidence_status.current_email_blocked_by == [] and (.emails[0].contact_evidence.record_fingerprint | type == "string" and length == 64)' "$PC68_YAMADA_DIR/邮件输入.json"
   jq -e --arg dir "$PC68_SATO_DIR" '.schema == 3 and .kind == "professor-contact-email-input" and .professor == "佐藤花子" and .professor_dir == $dir and (.emails | length == 1) and .emails[0].email_id == "佐藤花子::DIR00001::DIR00001_1" and .emails[0].contact_evidence.record.verdict == "confirmed_cross_source" and .emails[0].contact_evidence.record.current_email == "hanako@example.edu" and .emails[0].contact_evidence.record.evidence_status.current_email_blocked_by == [] and (.emails[0].contact_evidence.record_fingerprint | type == "string" and length == 64)' "$PC68_SATO_DIR/邮件输入.json"
   ```

5. 两份 `_contact_verify.json` 的 `items` 均须有 `email`、`roster`、`season`、`header`、`subject_batch`、`schedule`、`consent` 七项，七项 verdict 都为 `confirmed`；`items.email.value` 分别为本教授冻结邮箱，核验时间为当前 UTC 时间，来源指纹须绑定当前 `info.json` 与 `boshu_analysis.json`。写入前设置 `PC68_VERIFIED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"`、`PC68_INFO_FP="$PC68_PROGRAM/info.json:$(stat -f %m "$PC68_PROGRAM/info.json")"`、`PC68_BOSHU_FP="$PC68_PROGRAM/boshu_analysis.json:$(stat -f %m "$PC68_PROGRAM/boshu_analysis.json")"`。用同一个 `jq` 函数分别生成两份文件：

   ```sh
   write_contact_verify() {
     professor="$1"
     email="$2"
     destination="$3"
     jq -n --arg verified_at "$PC68_VERIFIED_AT" --arg professor "$professor" --arg email "$email" --arg info_fp "$PC68_INFO_FP" --arg boshu_fp "$PC68_BOSHU_FP" '{verified_at:$verified_at,items:{email:{verdict:"confirmed",value:$email,sources:[{type:"synthetic"}]},roster:{verdict:"confirmed",value:$professor,sources:[{type:"synthetic"}]},season:{verdict:"confirmed",value:"spring 2027",sources:[{type:"synthetic"}]},header:{verdict:"confirmed",value:"synthetic header",sources:[{type:"synthetic"}]},subject_batch:{verdict:"confirmed",value:"synthetic subject",sources:[{type:"synthetic"}]},schedule:{verdict:"confirmed",value:"synthetic schedule",sources:[{type:"synthetic"}]},consent:{verdict:"confirmed",value:"synthetic consent",sources:[{type:"synthetic"}]},warnings:[]},source_fingerprints:{info_json:$info_fp,boshu_analysis:$boshu_fp}}' > "$destination"
   }
   write_contact_verify "山田太郎" "taro@example.edu" "$PC68_YAMADA_DIR/_contact_verify.json"
   write_contact_verify "佐藤花子" "hanako@example.edu" "$PC68_SATO_DIR/_contact_verify.json"
   ```

   对两个本地邮件包分别运行阶段5计划预检，保留 JSON 输出并检查 `status` 和本教授的 `verify` 均为 `ok`：

   ```sh
   uv run --offline --no-project python "$PC68_SCRIPT" stage5-plan --program-root "$PC68_PROGRAM" --email-pack "$PC68_YAMADA_DIR/邮件输入.json" --email-id "山田太郎::DIR00001::DIR00001_1" --profile "$PC68_PROFILE" --template "$PC68_TEMPLATE" --followup-template "$PC68_FOLLOWUP_TEMPLATE" --mode both > "$PC68_RUN_ROOT/stage5-yamada.json"
   jq -e '.status == "ok" and .verify["山田太郎"] == "ok"' "$PC68_RUN_ROOT/stage5-yamada.json"
   uv run --offline --no-project python "$PC68_SCRIPT" stage5-plan --program-root "$PC68_PROGRAM" --email-pack "$PC68_SATO_DIR/邮件输入.json" --email-id "佐藤花子::DIR00001::DIR00001_1" --profile "$PC68_PROFILE" --template "$PC68_TEMPLATE" --followup-template "$PC68_FOLLOWUP_TEMPLATE" --mode both > "$PC68_RUN_ROOT/stage5-sato.json"
   jq -e '.status == "ok" and .verify["佐藤花子"] == "ok"' "$PC68_RUN_ROOT/stage5-sato.json"
   ```

   若返回 `needs_refresh`、`verify_missing` 或其他问题，先修复准备材料并保留记录，不发送正式请求。
6. 每位教授的用户选择完整且相互可区分：

   | 邮件编号 | `first_choice` | `signature_name` | `learning` | `initial_sent_date` | `email_address` |
   | --- | --- | --- | --- | --- | --- |
   | `山田太郎::DIR00001::DIR00001_1` | `true` | `测试申请者甲` | `地域交通规划` | `2026-10-01` | `taro@example.edu` |
   | `佐藤花子::DIR00001::DIR00001_1` | `false` | `测试申请者乙` | `沿岸防灾信息` | `2026-10-02` | `hanako@example.edu` |

   两封结果应分别保留对应教授自己的方向、想法、署名、学习内容及邮箱；不能把另一位教授的这些内容作为参照输入给生成代理。

### 4.3 请求与结果读取

1. 正式输入是一条普通第五阶段用户请求，其业务对象固定如下；发送时把 `<PC68_PROGRAM>` 替换为本轮程序根绝对路径：

   ```json
   {
     "folder_path": "<PC68_PROGRAM>",
     "professors": ["山田太郎", "佐藤花子"],
     "mode": "both",
     "choices": [
       {
         "email_id": "山田太郎::DIR00001::DIR00001_1",
         "first_choice": true,
         "signature_name": "测试申请者甲",
         "learning": "地域交通规划",
         "initial_sent_date": "2026-10-01",
         "email_address": "taro@example.edu"
       },
       {
         "email_id": "佐藤花子::DIR00001::DIR00001_1",
         "first_choice": false,
         "signature_name": "测试申请者乙",
         "learning": "沿岸防灾信息",
         "initial_sent_date": "2026-10-02",
         "email_address": "hanako@example.edu"
       }
     ]
   }
   ```

   请求正文要求分别根据两位教授自己的本地邮件包，以及本轮提供的合成申请人资料、首封模板和跟进模板完成两类邮件；产品按当前工作目录的默认查找规则读取这些文件。这样正式请求实际使用与预检相同的资料和模板。请求只写业务目标和用户选择，不命令代理执行特定内部工具步骤；本次运行按第2节和第3.3节检查实际委派、两个正式子任务、教授本地业务产物、总览内容、最终回复及清理行为，不证明根代理内部读取过程。
2. 在生成正式请求前，确认三个资料路径与正式请求工作目录完全一致，并且文件存在且可读：

   ```sh
   test "$PC68_PROFILE" = "$PC68_CONSUMER/套磁邮件/套磁信息.md" && test -f "$PC68_PROFILE" && test -r "$PC68_PROFILE"
   test "$PC68_TEMPLATE" = "$PC68_CONSUMER/套磁邮件/套磁模板.md" && test -f "$PC68_TEMPLATE" && test -r "$PC68_TEMPLATE"
   test "$PC68_FOLLOWUP_TEMPLATE" = "$PC68_CONSUMER/套磁邮件/套磁跟进模板.md" && test -f "$PC68_FOLLOWUP_TEMPLATE" && test -r "$PC68_FOLLOWUP_TEMPLATE"
   ```

   阶段4预检显式使用 `$PC68_PROFILE`；两次阶段5预检使用同一 `$PC68_PROFILE`、`$PC68_TEMPLATE` 和 `$PC68_FOLLOWUP_TEMPLATE`。正式请求的 `--cd "$PC68_CONSUMER"` 与产品默认查找位置一致。任何文件缺失或路径不一致时停止，不发送请求。确认后，使用仓库中已固定的第五阶段提示词模板和请求构建器生成请求；构建器将唯一的 `<PC68_PROGRAM>` 替换为本次 `$PC68_PROGRAM`，并在运行目录保存模板副本、渲染后的提示词、摘要和 `request.json`：

   ```sh
   uv run --no-project python \
     "$PC68_RECIPE_ROOT/.apm/skills/professor-contact/tests/runtime/build_issue68_eval_request.py" \
     --consumer-root "$PC68_CONSUMER" \
     --program-root "$PC68_PROGRAM" \
     --template-copy "$PC68_RUN_ROOT/prompt-template.txt" \
     --rendered-prompt "$PC68_RUN_ROOT/prompt.txt" \
     --hash-file "$PC68_RUN_ROOT/prompt.sha256" \
     --output "$PC68_RUN_ROOT/request.json" \
     > "$PC68_RUN_ROOT/request-build.json"
   jq -e '.status == "ok" and .template_sha256 == "2da8b43fe99f0d4481046bd13020f74374a90b155704b861cbd14eb86205f153" and .timeout == 900' "$PC68_RUN_ROOT/request-build.json" || exit 1
   jq -r '.command' "$PC68_RUN_ROOT/request.json" | uv run --offline --no-project python -c 'import shlex, sys; argv = shlex.split(sys.stdin.read()); raise SystemExit(0 if "--ephemeral" not in argv else 1)' || exit 1
   ```

   构建器及其单元测试必须先删除 `--ephemeral`；请求需要保存根任务记录，供产品按既有原生委派入口建立并运行子任务。上面的检查使用 `jq` 读取 `request.json` 的 `command` 字段，再按命令行参数规则解析，只有准确参数列表中不存在 `--ephemeral` 才能继续。检查失败时停止，不发送请求，交本地测试工程师修正请求步骤并重新进行第二关口复核。

   使用现有评估服务的 `POST /eval`，响应写入 `$PC68_RUN_ROOT/response.json`。不直接执行 `codex`。构建器固定加入 `--sandbox workspace-write`，使正式请求能够在隔离消费者内生成本次业务文件；该固定值属于本轮执行配置，不是验收目标。请求使用上一步已写明的项目信任参数加载消费者测试配置，不追加 `--model`、模型或推理的 `--config` 覆盖、并发参数，也不追加固定值之外的沙箱覆盖。在已配置的 `eval-server` 仓库工作目录执行 `direnv exec . sh -c 'curl -sS -X POST "http://127.0.0.1:${EVAL_PORT}/eval" -H "Content-Type: application/json" --data-binary @"$1"' sh "$PC68_RUN_ROOT/request.json" > "$PC68_RUN_ROOT/response.json"` 提交一次替代请求并保留响应。
   3. 从同一响应检查实际委派和两个正式子任务。读取 `.output.app_server_events[]` 中 `message.method == "rawResponseItem/completed"` 的项目；`message` 若为字符串先用 `fromjson` 解析，若为对象则直接读取。筛选 `params.item.type == "function_call"` 且 `name == "spawn_agent"` 的事件，把 `arguments` 按相同规则解析，并核对每次调用的 `agent_type == "professor-contact-email-generator"`。按 `call_id` 配对 `function_call_output`，取得两次成功返回的子任务编号，再关联 `.output.child_thread_reads` 核对每个子任务的 `thread_id`、`parent_thread_id`、`relation_kind`、读取请求、任务元数据和 `error`。必须有两条成功的、分别面向山田太郎与佐藤花子的委派，并对应两个均归属于本次根任务且无读取错误的正式子任务。教授身份由任务名称等非提示词字段、本地教授目录和固定输入交叉核对。`output.child_thread_reads` 的读取请求固定使用 `includeTurns: false`，只提供关系和任务元数据；不得从中取得或推断子任务业务正文，也不把它当作根代理内部读取或消费的证明。若现有响应字段不能对应准确委派和正式子任务，相关项记为无法判断，不以根代理最后一句话单独推断，也不另造采集方式。
4. 检查 `$PC68_RUN_ROOT/consumer/testdata/program/教授研究/工学/山田太郎/` 与 `$PC68_RUN_ROOT/consumer/testdata/program/教授研究/社会情報/佐藤花子/` 下各自的 `套磁邮件.md`、`套磁邮件.txt`、`套磁跟进邮件.md`、`套磁跟进邮件.txt`、`套磁邮件状态.json` 与 `_contact_verify.json`。从两位教授本地状态的 `emails[<本教授 email_id>]` 读取首封及 `followup` 条目的 `files`、`choices`、`model_result`、`validation`；用 `jq` 核对本地归属和完整文件路径，再人工对照邮件内容是否分别对应本人的合成研究材料及上述选择。
5. 总览由普通产品入口最多调用一次。用 `jq` 从 `.output.app_server_events[]` 提取 `stage5-rebuild-overview` 的 `commandExecution` 事件并确认调用次数为1；检查接口返回的 `overview_md`，以及 `$PC68_RUN_ROOT/consumer/testdata/program/教授研究/套磁邮件总览.md`，记录实际返回的 `status`、`overview_md`、`professors`、`emails`。只有总览返回和文件均包含本次已经写入本地状态的山田太郎与佐藤花子结果，才确认“结果完成后生成总览”这一可观察业务结果；不比较 `child_thread_reads` 或 `output.events` 中不存在的 `runtime_seq`，也不另行证明根代理内部等待或读取。若总览内容不能确认包含本次两份结果，相关项记为无法判断或按实际业务不符记录。
6. 本次业务完成后，确认本请求创建的选择分配、单教授交接及结果传递文件已清理。检查本次响应中出现的传递目录与文件路径；已知消费者临时目录 `$PC68_RUN_ROOT/consumer/.tmp-stage5` 必须不存在，其他已识别的本请求传递路径也不得残留。测试人员不代替产品删除传递文件，不搜索或清除其他请求的文件；清理失败单独记录，不覆盖教授业务结果。
7. 根代理最后回复从同一次接口响应读取：`jq -r '[.output.events[] | select(.type == "item.completed" and .item.type == "agent_message")] | last | .item.text' "$PC68_RUN_ROOT/response.json"`，再按第3.3节逐项对照，不得把总览返回当作教授业务结果。
8. `$PC68_RUN_ROOT/response.json` 保留本次接口响应供检查。仅使用其中与本次验收项相关的事件和结果，不采集新的追踪记录、制作完整调用链、读取子代理真实提示词或另存传递路径记录；观察过程中不得阻止产品清理。

### 4.4 停止与重试

第四十八版之后含 `--ephemeral` 的正式请求作为一次已保留的错误尝试，不得删除或改写；其根任务虽完成，但没有建立子任务或产生教授业务结果，辛记为无法判断。第五十四版只安排一次替代正式业务请求。该请求提交或状态不明后，不重发、不改提示、不换模型、配置、输入、消费者或结果；先确认服务响应与是否已产生业务文件。已确认的业务失败保留原样并交实现负责人，后续只复验受影响项。服务未接收请求且能证明无业务副作用时，按项目约定记录为未执行或外部阻塞，仍须先修订计划并再次过第二关口；不得将配置问题改写成产品失败。预检只检查当前产品提交的支持安装、输入有效性、既有配置来源和服务可调用性，不发送模拟业务请求，不启停服务。

第四十八版正式请求发送前的历史准备记录如下：第四十四版已在隔离消费者内把三份申请人资料及模板放到正式请求工作目录，文件内容与原合成材料的摘要一致。使用锁定产品提交重新运行第三阶段前置资料生成，两位均成功；第四阶段总状态为 `ok`、两位教授结果均为 `ok`；两份第五阶段预检均为 `status: ok` 且各自 `verify: ok`。因此，预检与正式请求的工作目录和文件位置现已对齐。2026-10-09，本地测试工程师在隔离消费者完成本地预检：阶段2/3合成前置资料生成成功，联系方式证据为 `fresh` 且两位均为 `confirmed_cross_source`；阶段4总状态和两位教授结果均为 `ok`；两份阶段5预检均为 `status: ok` 且各自 `verify: ok`。`EVAL_PORT` 环境值解析成功，端口接受 TCP 连接。消费者的两个锁定提交正确，指定模型和推理强度已写入，安装生成的其余配置保持不变。当时尚未发送正式请求，第四十八版第二关口曾通过；随后正式请求及结果见[正式运行记录](issue68-test-execution-2026-10-09.md)。这些旧状态不代表第四十九版第二关口有效，当前状态以第6节为准。

## 5. 失败处理与结束

结果只分通过、业务失败、无法判断、未执行。已确认业务失败优先保留；后续清理、网络、缓存或记录错误另行说明，不覆盖失败。辛预期正常完成，不能以核验未完成代替正常路径通过；教授如实返回问题不自动意味着根代理汇报错误，两者分别判断。输出与输入不符、业务未完成或第3.3节所列报告错误，按实际事实记录，不推断子代理提示词。

每次正式尝试均保留。业务失败后不因结果不满意重发请求；需要产品修正时交产品实现负责人，修正后只复验受影响项。外部故障按项目既有重试约定处理：先确认请求是否已发送、是否可能重复副作用；请求状态未知时暂停，不偷偷重发。准备错误由本地测试工程师修正，经确认后继续，保留原问题与变更说明。

甲至庚的有效复用结果保留通过归属；辛在当前产品上补齐有效通过结果、范围内已确认业务问题处理完成后，才交第三关口并结束测试。计划设计批准不代表第二关口、第三关口或合并通过。

## 6. 本轮交付状态

| 内容 | 状态 |
| --- | --- |
| 当前计划 | 第五十四版；计划设计已通过；第二关口待复核；本文件 |
| 计划设计审核 | 第四十版至第五十三版审核均保留历史归属。第五十四版改为安装目标分支当前版本并从锁文件冻结实际产品提交，同时更正正式规则来源；计划设计已通过，见[第五十四版设计审核记录](issue68-test-plan-r54-design-review.md) |
| 甲至庚 | 引用有效历史通过，保留原版本与来源 |
| 辛 | 第四十八版之后的正式尝试因请求含 `--ephemeral` 而未建立子任务，两位教授邮件及阶段5状态文件均未生成，当前为无法判断；详见[正式运行记录](issue68-test-execution-2026-10-09.md)。R44 历史准备结果继续保留原归属；第五十四版保留一次替代业务复验，检查准确委派、两个正式子任务、教授本地业务产物、包含本次两位教授结果的总览、清理及最终回复，不证明根代理内部读取过程 |
| 第二关口 | 第四十八版结论因未发现请求构建器的 `--ephemeral` 与原生委派冲突而失效；构建器和6项对应单元测试现已不含该参数，五模块128项回归亦已有通过记录。第五十四版改变产品版本取得与冻结步骤，当前第二关口待复核 |
| 第三关口 | 辛的当前结果为无法判断，替代正式业务产物复验待补；尚未通过 |

第四十七版调整第4.3节的请求构造命令及计划版本状态：固定提示词由请求构建器生成，移除对未赋值 `$PC68_PROMPT` 的依赖。第四十八版只修正固定沙箱参数的文字说明和审核状态。第四十九版记录已发生的错误正式尝试，禁止正式请求使用 `--ephemeral`，并增加提交前的准确参数检查。业务目标、必测项、预期结果、检查方式和通过条件均未改变。合成输入及预检输出留在隔离运行目录，不作为产品代码或验收测试提交。

第四十八版正式请求发送前的修订依据：用户明确本地测试工程师应完成计划内准备并推送拉取请求。第四十一版将先前列为待确认的阶段2/3前置资料和阶段4教授本地邮件包来源改为已执行的合成准备步骤，记录固定产品提交、联系方式证据及两份阶段5预检结果。第四十二版关于审批适配器测试契约的记录已撤销；第四十三版改记本机 Codex 默认值已设置为 `gpt-6-luna`、低推理强度，但该本机设置没有证明评估服务的实际配置。第四十四版根据路径复核发现，旧预检把申请人资料和模板放在消费者工作目录之外；本版将它们移入正式请求工作目录，重跑第三至第五阶段本地准备和预检并通过。第四十六版补齐已确认的测试配置文件来源和消费者加载命令。业务目标和甲至辛矩阵不变。当时正式 `/eval` 请求仍等待第二关口审核及明确授权；其后正式请求及结果见[正式运行记录](issue68-test-execution-2026-10-09.md)，当前状态以第6节和第五十四版修订记录为准。

第四十七版根据实现符合性复核发现，将原计划依赖未赋值 `$PC68_PROMPT` 的请求命令改为调用已推送的固定提示词请求构建器；记录固定模板摘要和本次构建成功条件，消除空提示变量对正式请求构造的影响。不改辛的业务目标、检查方法或通过条件，也不据此宣布第二关口或第三关口通过。

第四十八版修正第四十七版第4.3节中的文字冲突：构建器继续固定使用 `--sandbox workspace-write`，计划明确该固定值用于隔离消费者内的业务文件写入，并禁止追加其他沙箱覆盖。本次不修改构建器、提示词、业务输入、预期结果、检查方式、配置、重试条件或正式请求次数。

第四十六版修订说明：计划编写者此前未写清测试配置文件和加载步骤，又误把缺项表述为评估服务配置认证。推送前远端第四十五版已新增配套测试配置，本版保留并直接引用该文件，以两项设置合入消费者配置，保留安装代理及工具定义；撤销服务配置认证和为配置另建共享文件的要求。甲至辛目标、输入、预期及业务检查方式不变，已有资料路径准备和甲至庚结果继续复用。本段记录的是第四十六版计划修订当时的状态，不代表本轮后续操作。

第四十八版正式请求发送前的执行记录（2026-10-09）：用户确认采用本拉取请求中的配置文件。隔离消费者通过 `apm init -y --target codex` 及固定提交的 `apm install` 创建；第一次安装遇到 HTTPS 连接中断，原命令重试成功。锁文件中的 `professor-contact` 和 `professor-research` 提交分别为 `72f20846e9810f5445c0c6a3891f3877b4cd0e21` 和 `a9e7ffbc070dcfdc7b225e5e70de1b4576649ecd`。使用版本化 TOML 文件合入两项配置，并以 TOML/JSON 解析比较确认安装原有配置未改变。此后在同一隔离消费者生成合成前置资料和联系方式证据，阶段4两位结果均为 `ok`，阶段5两份结果均为 `status: ok` 且各自 `verify: ok`；解析评估服务端口并确认 TCP 连接成功。运行目录保留安装命令、退出码、日志、阶段结果及配置比对文件。当时未运行确定性验收套件、尚未发送正式 `/eval`，第四十八版限定设计复核与第二关口曾通过，正式请求仍待授权；这些均为历史状态，当前状态以紧接其后的第四十九版修订记录为准。

第四十九版修订记录（2026-10-09）：第四十八版之后已发送一次正式 `/eval` 请求，原始记录位于 `/private/tmp/pc68-task-20261009.U3yrne1G/run-Yo9u50JZ/`，仓库记录见[正式运行记录](issue68-test-execution-2026-10-09.md)。解析 `request.json` 后确认 `command` 的准确参数包含 `--ephemeral`；解析 `response.json` 后确认根任务编号为 `01a120fc-240d-7ea1-82bd-6e58acefb738`，两次 `spawn_agent` 均因该根任务没有可读取的记录而失败，子任务列表为空，没有教授业务产物。该次结果保留为测试步骤错误导致的无法判断。第四十九版撤销原第二关口结论；请求构建器和对应单元测试删除 `--ephemeral`、本计划设计复核及第二关口重新通过之前，不得发送替代正式请求。

第五十版修订记录（2026-10-10）：按最新审核意见，把真实委派、每位教授子任务结果的完成与消费、总览调用顺序和本次传递文件清理纳入同一次辛正式运行检查；只读评估响应已有事件、子任务读取结果、业务文件及文件状态，不新增采集器或单独运行。旧第三十七版因交接观察受阻，不能替代这些检查。隔离 T59 缺陷子项后，五模块128项回归及请求构建器6项单元测试均已通过；具体输出和仓库外日志见正式运行记录。计划设计复核及第二关口复核尚未完成，替代 `/eval` 请求不得发送。

第五十一版修订记录（2026-10-10）：按第五十版计划设计审核意见，明确逐次核对 `agent_type == "professor-contact-email-generator"`，通过 `call_id` 对应委派返回、用返回的子任务编号关联已完成且已读取的结果，并以现有字段核对教授身份和总览先后顺序。若响应缺少必要关联字段，记录为无法判断；不读取真实提示词，不另造采集方式。第五十一版计划设计审核已通过，第二关口复核尚未完成，替代 `/eval` 请求不得发送。

第五十二版修订记录（2026-10-10）：验收决定人指出，单独证明根代理内部等待并消费结果不符合测试规则和项目共识。本版保留 `AD68-1` 的产品行为要求，但删除把 `output.child_thread_reads` 解释为根代理读取证明以及用不存在的 `runtime_seq` 还原内部消费顺序的条件。`output.child_thread_reads` 只用于取得和对应两份子任务终态结果；测试通过两位教授业务产物、包含本次两份结果的总览返回与文件、以及根代理最终回复是否准确反映两份结果，判断可观察业务使用情况。甲至庚、辛的输入和正式请求次数不变，不新增采集器、运行或业务场景。第五十二版计划设计审核已通过，见[第五十二版设计审核记录](issue68-test-plan-r52-design-review.md)；第二关口复核尚未完成，替代 `/eval` 请求不得发送。

第五十三版修订记录（2026-10-10）：计划审核发现固定评估服务对每个正式子任务执行 `thread/read` 时使用 `includeTurns: false`，`output.child_thread_reads` 只含子任务关系和任务元数据，不能提供第五十二版要求的子任务业务正文。本版把该字段限制为核对子任务编号、父任务、关系类型、读取请求、任务元数据和错误，删除取得或比较两份子任务业务正文的步骤。教授身份及业务完成情况改由两次准确委派、教授本地目录、固定输入、各自邮件文件及本地状态核对；根代理对结果的可观察使用情况继续由总览和最终回复与业务产物的一致性判断。甲至庚、辛的输入、预期结果、一次正式请求上限、停止条件及通过标准不变，不新增采集器、运行或业务场景。第五十三版计划设计和第二关口均已通过，见[第五十三版设计审核记录](issue68-test-plan-r53-design-review.md)及[第五十三版第二关口复核](issue68-test-plan-r53-gate2-review.md)；替代 `/eval` 请求仍须取得明确授权后才能发送。

第五十四版修订记录（2026-10-10）：计划不再把持续变化的拉取请求永久固定到旧产品提交。正式安装改用第72号拉取请求分支 `codex/issue-68-stage5-per-professor` 的当前版本，安装后立即从消费者 `apm.lock.yaml` 读取并记录实际 `resolved_commit`，将该值冻结为本次 `PC68_PRODUCT_SHA`；同一次运行不重新安装或再次解析分支。分支随后变化时只分析受影响目标，不自动废除未受影响结果。正式依据改为任务工作区指定的 `Test Engineer Rule.md`、`PROJECT_CONSENSUS.md` 和适用于设计复核的 `Plan Reviewer Rule.md`，不再以旧计划或审核意见代替当前规则。本次不改变甲至辛的业务目标、输入、预期、检查方式、一次正式请求上限或停止条件，不新增测试、采集器或正式运行。第五十四版计划设计已通过，见[第五十四版设计审核记录](issue68-test-plan-r54-design-review.md)；第二关口待复核，替代 `/eval` 请求仍须在第二关口通过并取得明确授权后才能发送。
