# 第66号议题／第73号拉取请求测试计划

版本：`issue-66-test-plan-new-rules-r4.10-2026-10-09`。

产品基线：`86b6c82197e1b0afdbc9c337b6c4892b37ddc78d`。本版保留既有A—D结果及R4.8范围，沿用R4.9新增的完成报告源文件与安装件检查，并按项目共识修正E组评测端口接线。R4.9复核的产品候选 `b4c6f46537241cb062c7088989adbd07f30553fb` 尚未同步第十六版契约，新增契约检查在该源码上有两项失败。R4.10审核后，PR 新增产品候选 `6aa2c8b23f9a723fff1b862851eb49b72a4c9a1d`；执行人仍须先按本版记录其完整提交值并完成源文件与安装件检查，检查通过前不得发送新的 `/eval` 请求。

## 依据与范围

- 采用工作区有效的《测试工程师规则》和《项目共识》。正式需求采用[第一关口第六版](https://github.com/ScholarWorkflow/professor-contact/issues/66#issuecomment-5988663001)，加验收决定人2026年10月9日删除最终消息逐字节复制要求的调整；实施依据采用[第十六版完整执行计划](issue-66-implementation-plan.md)。第十五版及其批准记录只作历史来源，不再要求实施者拼接旧正文。
- 正式状态是教授目录内的 `套磁候选状态.json`，本地候选稿是 `套磁想法候选.md`，总览只是派生展示。凭据及校验交接文件不能替代正式状态。
- 只检查第三阶段及直接改变的第四阶段读取入口。教授姓名按唯一处理；非 Codex 运行、同名消歧、断电或强制终止恢复、同教授并发写入、其他阶段改造和全仓回归不列入必测。第48号议题不是前提。
- 第一版14项合并为下面5组，合并检查和结果复用，不安排14组独立运行。一次真实代理运行只检查代理职责；代码能够确定的输入、保存、修正和轮次计算不再用模型重复证明。
- R4.7按用户确认澄清E组通过条件：流程是否符合本次修改目标，与候选内容是否通过白话校验分别判断；不增加测试或模型请求。R4.8进一步删除校验子代理最终消息与文件逐字节相同的要求：固定写入文件是唯一正式校验原文，最终消息只报告写入结果，不参与保存或记录。已有且范围外的内容问题须报告，但不直接判为本次流程目标失败。

## 唯一必测清单

| 组 | 业务目标 | 输入或场景 | 预期结果 | 主要检查入口 |
| --- | --- | --- | --- | --- |
| A | 当前教授独立提交，两文件普通失败恢复正确，第四阶段读取指定教授 | 合法生成；总览人工改动；第二份正式文件安装失败；提交后清理失败；自己的候选稿人工冲突；第四阶段指定甲 | 总览冲突不挡甲，不依赖其他教授状态或共享登记；提交前失败恢复旧两文件，提交后清理失败保留新两文件；自己的冲突拒绝覆盖；第四阶段只从甲正式状态取候选 | 保存与读取入口的确定性检查及必要源码核对；所列代表场景详见下文，优先复用有效历史结果 |
| B | 正式状态稳定重建总览，错误时不发布部分内容，旧身份兼容准确 | 甲乙同方向／组编号；总览删除；一个现存状态损坏；总览冲突或写入失败；旧身份匹配一个、零个、多个记录 | 行、教授链接及排序正确，只用已提交状态；错误时旧总览保留；一个匹配只迁移身份、保留候选，零个或多个匹配在写总览前拒绝 | 重建／兼容入口检查业务行和旧总览；源码确认写入目标，不比较所有教授文件快照 |
| C | 凭据固定输入，修正只处理点名对象，保留旧行为及两轮上限 | 正常首轮及修正；混传来源、摘要／来源变化；新调用、同调用同轮重复准备、第二轮准备；问题指向首轮选择外方向、单组或文件；首轮通过、修正通过、第二轮失败；旧显式选择／跳过／修正 | 同凭据消费原输入，错误拒绝；路径按调用／轮次隔离，重复准备拒绝；修正来自问题，不重放首轮过滤，组问题不扩大，文件问题按渲染对象展开；保留无关候选及记录；首轮通过不修正，第二轮终态无第三轮；旧准入／筛选语义保留 | 凭据、计划、提交、记录入口的确定性检查；比较必要任务集合、状态字段和候选内容，不为修正组合追加模型请求 |
| D | 固定写入、保存和记录传递同一校验原文，按教授准确消费，失败不推进状态 | 三种合法结论及特殊字符；单文件／批量映射；完整批量正文逐教授消费；错教授／凭据／轮次／摘要、候选稿变化、原文不完整；非法输入／映射、既有文件／符号链接、写入／读回失败、批量后项失败；旧无输出路径及旧记录入口 | 完整对象语义保留，输出与文件字节相同、权限 `0600`；保存不重排；记录消费本教授唯一条目并推进本教授轮次，乙异常不阻甲；错误不推进相关状态、不覆盖既有目标，批量只清理本次未完成文件；旧接口兼容 | 正式写入／保存／记录入口；`jq` 检查必要字段、直接比较字节、标准框架安排文件故障，详见下文 |
| E | 根对话及命名子代理按实际结果推进流程 | 产品同步后一次正常第三阶段请求，受支持的干净消费者；只检查实际通过或修正分支 | 生成子代理完成候选保存；校验子代理调用固定写入，最终只返回规定的完成报告；根消费正确教授和本轮交接文件，依次准备、保存、记录；按记录结果修正或停止，终态后尽力重建一次总览；一轮通过、修正后通过或两轮仍失败均可成为合法终态，不要求候选内容一定通过 | 固定写入报告契约定向测试；安装件报告检查；当前实现的评估服务中的必要调用、命令结果、固定写入文件及教授最终状态；按下文区分流程结果与内容结论，不读取或推断子代理收到的提示词，只发一次模型请求；既有运行只复用未受影响事实 |

## 检查方法及必要性

### A：分别检查代码依赖、子代理路径和根的交接

旧保存函数并非因为调用者传错路径而碰到共享文件。在基准版本 `03dfd501f5212c86356409f7e011f676384f2633` 中，`cmd_stage3_finalize` 收到正确程序目录后，仍调用 `load_projections(program_root)`，拼出总览路径检查冲突；冲突会在当前教授保存前返回。当前实现已移除这段依赖，改用当前教授的两文件提交。

因此保留“总览人工改动仍能完成当前教授”的一个代表性回归检查，结合源码确认保存不读取其他教授状态、不访问共享登记、不依赖程序根锁及第48号议题。删除分别破坏乙状态、总览、共享登记的重复运行，不另设“子代理随意改别人文件”的模型测试。子代理使用的教授路径，在E组用可见保存命令和返回结果确认；根是否消费错交接对象，也在E组单独确认。

两文件失败恢复直接测代码：在临时教授目录准备旧候选稿和旧状态，记下两文件字节；给保存入口合法的新结果。用标准测试框架让“安装第二份正式文件”的操作失败一次，随后恢复操作允许成功。预期返回 `local_pair_commit_failed`，两文件都与旧字节相同，不留下“新稿配旧状态”。不让磁盘真的故障，不让模型重试，不测断电。提交后临时文件清理失败用有效历史结果或一个对应断言确认新两文件保留。

自己的候选稿人工冲突及第四阶段读取甲优先复用有效结果；补查时只调用对应入口，不跑后续邮件。模型重试可以处理一次失败，却不能代替本次新增恢复代码的这个检查。

### B：总览完整只指现存状态均成功读取

重建扫描现存状态；没有预期教授清单，也不会把某教授状态文件根本不存在判为漏交。测试不要求未实现的完整性检测。

正常重建检查甲乙业务行、链接、编号不混合及稳定排序；机器事实来自正式状态，不从候选稿或共享登记补造。损坏一个扫描到的状态文件时，预期拒绝且旧总览保留，不能发布只包含其余教授的总览。

总览人工冲突、写入失败和旧身份匹配的历史结果优先复用。多个旧身份匹配只指迁移歧义，不新增同名支持。源码确认重建唯一正式写入目标是总览，读取与身份整理不写教授文件；删除第一版所有教授文件逐字节快照要求。

### C：修正范围及两轮判断测代码

固定输入问题记录，调用修正计划检查任务集合；提交后比较未涉及方向、组及校验记录的必要字段。身份、编号、顺序、参与方向、引用和来源保留；来源、渲染或机器事实变化时拒绝，不部分提交。旧显式修正保留准入和筛选，普通生成保留原选择、跳过与未请求组删除行为。

轮次检查预先给定结论：首轮通过返回不需修正；首轮失败只修正点名对象；修正通过或第二轮仍失败都进入终态，禁止第三轮。复用有效历史修正及轮次结果，不因文档变化重跑。

批量代码接口存在，当前 Codex 校验路由按单教授准备交接。“甲已通过、乙需修正”只在确定性输入中检查各教授状态独立和第二轮任务筛选，并静态核对安装流程不会再派发终态教授。没有发现另加批量模型采样的必要事实，不把批量接口支持写成已发生的混用缺陷。E组只检查实际分支。

### D：原文从固定写入的输出开始比较

“保存”指根调用 `stage3-save-validation`，把校验子代理输出文件的原文复制到本轮记录使用的文件；它不再次保存候选稿。“记录”指根调用 `stage3-record-validation`，读取原文，将本教授的轮次、问题和校验状态写入 `套磁候选状态.json`，返回是否需要修正及是否终态。

固定写入文件是唯一正式校验原文。固定写入会按正式规则排版输入对象，因此不要求输入参数原排版与输出字节相同；两者使用标准 `jq` 结构相等判断 `jq -e -s 'length == 2 and .[0] == .[1]'` 比较完整 JSON 对象。对象字段顺序、缩进和末尾空白不影响该判断，数组顺序及各字段值必须相同。随后直接检查：

1. 将 `stage3-write-validation` 的标准输出原样保存为临时文件，用 `cmp -s` 与指定输出文件比较；批量每个文件保留同一完整对象。
2. 调用保存入口，用 `cmp -s` 比较源文件和交接文件，不解析后重排。保存入口使用元数据中的源、目标路径，测试不另传正文替产品交接。
3. 调用记录入口，用 `jq` 核对返回的原文摘要与保存结果一致，以及相应教授的轮次、问题、终态。摘要只用产品已有返回值，不新增关联平台；错误绑定或原文缺失时不推进状态。

三种合法结论均应写入成功，写入成功不等于校验通过。批量逐教授消费完整原文，不拆成新对象。文件故障、映射拒绝、既有文件保护只观察相应目标及正式状态，不扩大为全环境快照。不传 `output_file` 的旧校验指令仍只读，由安装指令静态检查；旧记录入口用兼容结果检查。

### 正常工作流程：由产品自行执行

固定写入不是测试专用动作。正式依据是本仓库技能文件的「Codex Stage 3 固定状态转移」和校验代理文件的「Stage-3 原文落盘」：[技能流程](../.apm/skills/professor-contact/SKILL.md)、[校验代理指令](../.apm/agents/professor-contact-style-validator.agent.md)。下表是正式流程的观察对照，不是让测试人员代执行命令。

真实运行只给一次正常第三阶段业务请求，指定隔离资料中的教授及正常业务输入；不在请求中列下表命令、提醒委派或补写保存逻辑。代理从受支持安装得到正式指令，自行完成流程。测试人员在运行结束后只读检查已有结果，不补执行遗漏的写入、保存、记录或修正。D组直接调用命令检查代码，E组观察代理自行调用，两者职责不同。

表中各命令均指安装后的 `contact_state.py` 入口。`I`、`IS` 是生成结果中本教授的 `invocation_file`、`invocation_sha256`；`H`、`HS` 是本轮准备返回的 `handoff_file`、`handoff_sha256`；`O` 是准备返回的 `output_file`；`V`、`VS` 是保存返回的 `validation_file`、`validation_sha256`。这些只是文档代号，执行参数必须来自对应实际结果，不由测试人员另造。

| 顺序 | 执行者 | 正常动作和参数来源 | 检查什么 |
| --- | --- | --- | --- |
| 1 | 根委派生成子代理 | `professor-contact-idea-generator` 按正常输入生成，自己调用 `stage3-plan`、`stage3-finalize` 保存候选稿及状态，最终返回本教授凭据 | 子代理实际保存成功；候选路径、正式状态及返回 `invocations` 对应业务教授；根不替它生成或保存候选 |
| 2 | 根 | `stage3-prepare-validation --invocation-file I --invocation-sha256 IS --round 1` | `I`、`IS` 来自该教授生成结果；完成结果成功，并返回本轮 `H`、`HS`、`O` 和候选稿路径 |
| 3 | 根委派校验子代理 | `professor-contact-style-validator` 校验候选稿；按安装指令执行 `stage3-write-validation --output-file O --result-json <完整校验对象>` | 实际写入命令使用本轮 `O`；命令成功，指定文件包含完整合法结果。成功消息恰为 `result=ok`、`write_status=written`、`output_files=[O]`；失败消息恰为 `result=error`、`write_status=failed`、本轮 `output_files` 及规定的 `reason_code`。带 `output_file` 的消息不得含 `files`、`verdict`、`issues`、`notes` 等校验正文字段，不与文件作字节比较。仅核对可见实际动作，不判断子代理收到的提示词 |
| 4 | 根 | `stage3-save-validation --handoff-file H --handoff-sha256 HS` | 使用本轮准备结果；复制校验原文成功，返回 `V`、`VS`，不重写候选稿 |
| 5 | 根 | `stage3-record-validation --handoff-file H --handoff-sha256 HS --expected-validation-sha256 VS` | `H`、`HS` 与保存同轮，`VS` 来自保存结果；记录成功，返回 `needs_correction`、`terminal`，正式状态对应校验结论 |
| 6 | 根按记录结果决定 | 无需修正则结束校验；需要修正则委派一次生成修正，继续使用 `I`、`IS` 和已记录的 `V`；修正保存成功后重新准备 `--round 2`，按3—5再校验、保存、记录 | 修正由记录结果触发，未换教授或凭据；第二轮使用新准备的交接信息；第二轮记录后停止，不发第三轮 |
| 7 | 根 | 终态后 `stage3-rebuild-overview --program-root <本次程序根>` 一次，然后汇报结果 | 使用业务程序根；总览失败只报告总览问题，不重跑生成、不反转教授终态 |

每一步非成功都停止依赖动作；尚未完成不能汇报成功。正常完成是一轮通过或一次修正后的终态，中途停止不是正常完成。实际未触发的修正或失败分支不另发模型请求。

这里的“非成功”指生成提交、交接写入、准备、保存或记录入口执行失败，不指完整校验结果中的 `verdict=fail`。合法失败结论仍须保存和记录，再按 `needs_correction`、`terminal` 推进；终态后的总览失败仍按尽力重建规则报告。

### E：观察实际动作，不依赖子代理收到的提示词

E组验证本次修改涉及的代理职责、交接、修正和停止流程，不把“候选内容最终一定通过白话校验”作为通过条件。两轮后仍有内容问题时，若修正遵守允许范围、两轮结果正确保存和记录、正式状态为 `fail_after_2_rounds`、没有第三轮生成或校验，并在终态后执行一次总览重建且如实汇报，则该分支符合流程预期；仍须检查下面各项，不能仅凭终态判整个E组通过。

执行记录分别写明E组流程目标的结果和候选内容的校验结论。已有且范围外的内容缺陷单独报告事实与影响，不要求本次修复，也不反转已成立的流程结论；本次修改造成的范围内缺陷仍记业务失败。缺少必要观察仍记对应事实无法判断。不得降低校验规则、忽略问题、改写失败结论或再次采样求通过。

只观察现有评估输出提供的下列事实，不从根写出的委派说明推定子代理实际收到什么：

1. 根实际委派给安装的准确命名生成／校验代理。生成子代理可见保存命令、返回教授路径及最终结果对应本次教授；正常一轮通过有2个直属子线程，一次修正有4个。仅检查确认的职责，不认证整个运行时。
2. 根用生成结果实际返回的教授目录和凭据准备校验；准备结果、后续保存／记录命令与返回教授、凭据、轮次对应。分别检查根拿错结果、传错路径，不用子代理提示词证明。
3. 检查先后关系：生成保存成功后才准备；校验者固定写入成功后才根保存；保存成功后才记录。比较相应完成结果与后续动作顺序，不要求某个等待工具，不统计等待次数。前一步失败不继续依赖动作、不自述成功。
4. 带 `output_file` 的校验子代理最终消息按第3步的固定字段检查成功或失败，以及 `output_files` 是否逐项等于本轮指定路径。若消息含校验正文字段，记本项失败。根不得从消息重建文件。固定写入参数对象与指定文件按D组使用 `jq` 比较结构，固定写入输出与文件、源文件与保存文件按D组比较字节。本项只检查 Codex 路径。
5. 解析记录命令的 `needs_correction`、`terminal`：需要修正且未终态时才允许修正生成及第二轮校验；首轮通过或第二轮终态后，无新生成／校验委派，也不再记录。修正继续用同一调用凭据，范围遵循C组已验证计划。比较记录完成后的实际动作；未触发分支不宣称真实运行，不发请求诱出分支。
6. 终态后只尽力重建一次总览。最终教授状态符合实际校验结论，清理或总览失败不覆盖已成立的业务结果。

结构化输出用 `jq` 按必要事件类型、编号、顺序判断，不凭文本关键词。只用服务已有的相应命令结果和委派信息；缺少必要动作、固定写入文件或规定完成报告时，说明缺少什么，受影响事实无法判断，其他结果仍可采用。静态检查不冒充代理已执行，实际路径不冒充未发生分支已通过。

### 根对话后续命令的具体检查步骤

采用既有评估服务响应及共享夹具 `configs/codex-eval-adapter-contract.json` 的契约 `skills-test-fixtures/codex-eval-adapter@16`。本次只需要根线程编号、相应工具调用／完成结果、必要子代理结果及顺序；不要求完整运行轨迹，不新增采集器。现有适配约定把根编号放在 `output.thread_id`，事件放在 `output.app_server_events`，事件序号为 `runtime_seq`，原始事件中的线程编号为 `message.params.threadId`，子线程只读元数据放在 `output.child_thread_reads`。这些是当前服务和契约版本的观察约定，不是要求产品固定私有运行时字段。

本地测试工程师在第二关步骤中固定实际响应文件与适用夹具版本。下例中的 `run_dir` 是按隔离步骤创建的仓库外运行目录，`eval-response.json` 是那一次正式请求的原始响应，不是另发请求获取的结果。对沿用上述约定的返回，可直接用 `jq` 取得根的现有调用及输出：

```sh
root_id=$(jq -er '.output.thread_id | select(type == "string" and length > 0)' "$run_dir/eval-response.json")
jq --arg root "$root_id" '
  [.output.app_server_events[]
   | select(.message.params.threadId == $root)
   | select(.message.method == "rawResponseItem/completed")
   | select(.message.params.item.type == "custom_tool_call"
         or .message.params.item.type == "custom_tool_call_output")
   | {seq: .runtime_seq, item: .message.params.item}]
' "$run_dir/eval-response.json"
```

这是直接查看已有结构化字段的命令，不是专用判定程序。只对照本目标涉及的准备、保存、记录、重建调用；命令可能位于执行工具的参数中，按实际工具载荷读取，不要求命令出现在某个预设顶层字段。不解析或执行日志里的代码，不把聊天正文中引用的命令当工具调用。其他适用返回形态按已有服务说明读取，不强行改造成此形态；缺少实际调用或完成输出时明确无法判断。

按 `@16` 契约，先从正式委派关系得到可归属的子线程。旧式路径只认事件中 `item.type=collabAgentToolCall`、`item.tool=spawnAgent` 的正式关系，发送方来自 `senderThreadId`，子线程来自 `receiverThreadIds`。当前多代理路径还可能用三项证据组成同一正式关系：发送线程的 `rawResponseItem/completed` 事件中有结构化 `function_call`（`name=spawn_agent`、`namespace=collaboration`、非空 `call_id`），同一发送线程上 `item.id` 等于该 `call_id` 且 `agentThreadId` 给出唯一子线程的 `subAgentActivity`，以及 `output.child_thread_reads` 中对应子线程的成功只读结果。读取包装必须满足 `thread_id` 等于子线程、`parent_thread_id` 等于发送线程、`relation_kind=subAgentActivity.agentThreadId`，且 `result` 是对象、`error` 为 `null`；该结果的 `thread.id`、`thread.parentThreadId` 和 `thread.source.subAgent.thread_spawn.parent_thread_id` 必须与正式关系相符且唯一。单独的子线程读取、`subAgentActivity` 或任务名都不能建立委派关系。

只对上述关系确定的子线程，把 `output.child_thread_reads` 成功结果中的 `thread.agentRole` 和 `thread.source.subAgent.thread_spawn.agent_role` 当作代理角色证据：一项存在时采用该值，两项都存在时必须相同。将其与消费者中唯一的同名合法代理定义对应，分别识别 `professor-contact-idea-generator` 和 `professor-contact-style-validator`。`agentPath` 可能只是委派任务名，不能拿来证明加载了哪个代理定义；两项角色字段冲突时记录证据矛盾，两项都没有时记为无法识别角色，不猜测也不补发请求。子线程的工具调用和完成结果按事件中的 `message.params.threadId` 对应到该子线程，再按 `runtime_seq` 排序；委派关系本身不代表子线程已完成。

逐步对照如下：

1. 用根线程编号选根的工具记录；按上文 `@16` 正式关系字段和子线程角色字段区分相应命名代理，再用 `message.params.threadId` 选取该子线程的工具记录。只取当前教授生成完成结果、校验固定写入结果及子代理完成状态，不读收到的提示词，不以根声称已完成代替调用结果。
2. 将生成最终结果的 `invocations` 中本教授凭据，与根准备命令参数直接比较；用候选稿／状态的规范父目录对应教授，不以展示名猜配。准备成功结果返回的交接文件、摘要和轮次，随后与保存和记录参数比较。
3. 将保存命令成功结果中的 `validation_sha256`，与记录命令的 `--expected-validation-sha256` 比较；记录结果中的 `validation_input_sha256` 应对应同一文件。摘要只检查保存和记录实际消费的文件绑定，不用于比较子代理最终消息。固定写入输出与文件、源文件与保存文件的字节比较按D组方法，不重新排版原文。
4. 对应工具调用和结果按实际调用编号或项目编号配对，再按事件序号检查：生成保存完成早于准备，固定写入成功早于根保存，保存成功早于记录。如果命令最初只返回运行中的会话编号，以后续最终完成输出和退出结果为准，不能当成功。若多个入口同在一次工具调用中，以可见执行内容及各自完成结果确认顺序；无法分清就不推定顺序成立。
5. 解析记录返回的 `needs_correction`、`terminal`，对照其完成后的实际委派和命令：无需修正没有新生成；需要修正且未终态才进入第二轮；第二轮终态后没有再生成、校验或记录。检查结束后的教授正式状态，及终态后的那一次总览命令。只判断本次实际分支。
6. 命令参数、对应完成结果或固定写入文件等某一必要事实不可见时，说明具体缺项并记该事实无法判断，不以最终状态倒推过程，不补调用求通过，不重复模型采样。子代理最终消息没有重复完整校验正文不构成材料缺口。已取得的其他业务结果可以保留。

以上是第三版的交接状态。第四版的实际请求接线、输入、配置、运行目录、适用事件形态和清理步骤见下文“执行步骤 R4.4”；此记录不代表第二关已批准。

## 执行准备与结果复用

第三版按原编号将1、2、6项并入A；3、4、5项并入B；7、8、12项生成兼容和14项代码轮次并入C；9、10、11项及12项校验兼容并入D；13项及14项实际代理行为并入E。第四版沿用已审核的必测清单和检查方法，只补齐本地命令、既有测试名称、环境准备、输出及失败处理；R4.1补齐 `@16` 子线程正式关系和角色读取方式，R4.2补齐读取包装字段核对，R4.3曾将运行路径改为环境变量并补记A组源码核对结果，R4.4移除与夹具V2不兼容的 `--ephemeral`，使用评测进程已配置的独立 `CODEX_HOME`，只通过项目配置设置信任等级，保持产品代码及已选夹具不变。R4.5根据用户要求在保留R4.3和R4.4结果的基础上追加一次独立请求；R4.6根据R4.5仍返回HTTP 504的情况，只把新请求的超时值从300秒延长至1200秒，其他产品、夹具、提示词、配置和A—E目标不变。R4.10删除R4.3引入但不符合项目共识的评测服务路径变量；历史运行事实继续保留，当前执行只采用下文R4.10入口。

本地测试工程师在本文件补齐实际断言或命令、合成输入、配置来源、输出位置、隔离清理、失败处理，提交第二关口。先核对[历史结果来源](https://github.com/ScholarWorkflow/professor-contact/pull/73#issuecomment-5981805377)、`test-plan/issue-66-results-history.md`、`test-plan/issue-66-runtime-attempts-20261007.md`；足以判断且行为未变的结果直接复用。旧212项通过不等于5组全通过，提交变化不使未变结果失效。

历史测试程序有的已从本分支删除；引用有效结果，或只恢复／补写本清单缺少的必要断言，不恢复整套测试及判定平台作为前提。两文件故障使用标准框架，不建设专用故障工具。

确定性检查在生产者仓库进行。模型运行从独立消费者开始，用支持的安装路径；有效安装复用，失效才重装，不复制或手工修补。Codex 使用既有评估服务，不启动、停止或重启；按工作区 `eval-server/README.md`、`eval-server/docs/appserver-migration.md` 接线。正式请求命令必须从已配置的评测服务工作区执行，并用 `direnv exec .` 向该次请求提供 `EVAL_PORT`；计划不另设评测服务路径变量，也不在正式请求外读取、保存或探测端口。评测进程启动时已使用独立 `CODEX_HOME`；请求不额外指定该目录或用户空间配置，只通过项目配置设置合成消费者的信任等级。请求不传模型或推理强度覆盖，沿用评测环境默认设置。提示词只提出业务请求，不补写产品流程。

临时输入、实际配置、必要原始输出放在仓库外独立临时目录；命令使用 `${TMPDIR:-/tmp}` 选择临时目录位置。目录隔离会话、资料和输出，不连接生产资料或无关进程。正式计划和必要脱敏结果入库，不上传敏感原文。不新增来源认证、完整轨迹、逐调用账本或通用证据能力检查。

## 失败、重试与完成

- 每个获批计划版本下，E组最多执行一次正式模型请求，不自动重试。R4.3、R4.4与R4.5的请求及无法判断结果均保留。R4.6使用新运行目录和相同的产品、夹具、提示词及项目配置，只将请求的 `timeout` 设为1200秒；此步骤需经第二关审核后执行一次。若请求仍遇到服务超时，记为无法判断并停止受影响事实，不再重试。
- 不因业务失败重新采样求通过。步骤错误停止并修正，产品问题交实现负责人；保留所有正式尝试，后续清理或网络错误不覆盖业务失败。
- 结果区分通过、业务失败、无法判断、未执行。遗漏记录先取原记录，待补不直接判产品失败，也不批准缺失结果。
- 第一关确认清单，第二关确认步骤可运行且无超范围要求，第三关确认当前有效结果。只复核受影响目标；必测全部有效通过、范围内缺陷处理后结束，本计划不作合并批准。

## 执行步骤 R4.4

### 本地确定性检查（A—D）

从 PR #73 当前分支仓库根目录开始。记录 `git rev-parse HEAD` 作为产品代码版本；测试代码和计划改动以本轮实际提交记录。先确认 `uv`、Python 3.12 可运行；依赖缓存和完整输出放在仓库外的独立目录。每个测试夹具使用系统临时目录并由标准测试框架清理；本地输出保留在运行目录，判断完成前不删除。此步骤不运行全仓测试。

以下一次命令执行42项定向检查：A、B使用新增的本地状态测试；C使用现存修正、凭据及摘要测试；D使用新增的固定写入、保存和记录测试；另执行一个总览冲突和三个第四阶段读入回归。

A组只读源码核对已完成：`contact_state.py` 第6919—6970行显示 `cmd_stage3_finalize` 从当前 `professor_dir` 读取输入包和候选状态；第7238行和第7276—7289行显示候选稿及状态文件均位于该教授目录，并在第7278行交由 `staged_pair_commit` 提交；第240行是该提交函数定义。第7268—7275行说明总览不由保存入口读取或写入，第7289行只将总览路径作为返回字段。结论：符合教授本地保存要求，总览不参与本地提交。

```sh
producer=$(pwd)
run_dir=$(mktemp -d "${TMPDIR:-/tmp}/issue66-pr73-local.XXXXXX")
git -C "$producer" rev-parse HEAD > "$run_dir/product-sha.txt"
cd "$producer/.apm/skills/professor-contact/tests"
set -o pipefail
UV_CACHE_DIR="$run_dir/uv-cache" uv run --python 3.12 --no-project python -m unittest \
  test_issue66_stage3_local_state \
  test_issue66_validation_handoff \
  test_stage3_validation_refine.Stage3ValidationIngestTests \
  test_issue66_r12_validation_input_sha.Issue66RecordValidationInputShaTests \
  test_contact_state.TestRunnerBasics.test_05e_overview_manual_edit_does_not_block_local_finalize \
  test_stage3_direction_groups.Stage3DirectionGroupTests.test_stage4_ordinary_selection_joins_by_direction_id \
  test_stage3_direction_groups.Stage3DirectionGroupTests.test_stage4_exactly_migrates_v1_candidate_state_with_pack_mapping_without_stage3_rerun \
  test_stage3_direction_groups.Stage3DirectionGroupTests.test_stage4_partial_other_professor_rerun_preserves_existing_selection_and_email \
  -v 2>&1 | tee "$run_dir/local-tests.log"
test_exit=$?
printf '%s\n' "$test_exit" > "$run_dir/local-tests.exit"
exit "$test_exit"
```

预期为42项全通过，退出码为0。日志末尾的 `Ran` 数应为42，`local-tests.exit` 应为 `0`。命令或依赖错误、数量不符、断言失败时保留原日志，停止把该项记为通过；只修正已确认的步骤问题后重跑受影响检查，不运行全仓测试。此前本轮曾执行三组拆分命令，其中一次既有回归方法名写错并已定位；正式候选以本节合并命令的结果为准。

### R4.4正式运行（E）

R4.4仅在第二关批准本节步骤后追加发送一次 `/eval` 请求。R4.3原始请求（含 `--ephemeral`）及“无法判断”结果保留为历史记录，不覆盖、不改写。正式运行不在生产者目录执行，不连接真实项目资料。使用 `${TMPDIR:-/tmp}` 在仓库外创建新的运行目录；其中的消费者必须位于生产者和所有工作树之外。消费者、程序资料和输出均为合成内容。

```sh
producer=$(pwd)
run_dir=$(mktemp -d "${TMPDIR:-/tmp}/issue66-pr73-eval.XXXXXX")
consumer="$run_dir/consumer"
program_root="$consumer/fixture-program"
# 与R4.3保持相同的产品代码版本，只修正请求选项。
producer_sha=fe1ac16194b3fd0890f02a8a3ad9c623aead5bc4
mkdir -p "$consumer"
cd "$consumer"
apm --version > "$run_dir/apm-version.txt"
apm install "ScholarWorkflow/professor-contact#$producer_sha" --target codex > "$run_dir/apm-install.log" 2>&1
```

执行 `apm --version` 并将版本写入运行记录；本轮准备时已确认为 `0.29.0`。安装必须从上面记录的精确提交选择器通过远端 APM 路径完成。安装失败即停止 E；不得改用本地路径、复制文件或手工修补。

安装完成后，用本分支的既有合成夹具生成程序资料和清单；程序根放在消费者内，清单放在运行目录：

```sh
UV_CACHE_DIR="$run_dir/uv-cache" uv run --python 3.12 --no-project python \
  "$producer/.apm/skills/professor-contact/tests/runtime/prepare_issue55_stage3_fixture.py" \
  --program-root "$program_root" \
  --output "$run_dir/fixture-manifest.json" > "$run_dir/fixture-build.json" 2>&1
```

读取现有提示词模板并只替换程序根路径，保存为 `$run_dir/eval-prompt.txt`。提示词必须仍只提出正常第三阶段业务请求，不得追加命令、委派指示或业务逻辑。评测进程启动时已使用独立 `CODEX_HOME`，本请求不设置或覆盖 `CODEX_HOME`；按夹具V2要求，命令不包含 `--ephemeral`。以下命令只通过 `--config` 给新消费者设置项目可信度，格式按评测服务支持的 `projects` 内联表，不使用带点号的动态路径键；不覆盖模型、推理强度或其他审批配置：

~~~sh
UV_CACHE_DIR="$run_dir/uv-cache" uv run --python 3.12 --no-project python -c 'import sys; from pathlib import Path; template=Path(sys.argv[1]).read_text(encoding="utf-8"); root=sys.argv[2]; assert template.count("{{PROGRAM_ROOT}}") == 1; Path(sys.argv[3]).write_text(template.replace("{{PROGRAM_ROOT}}", root), encoding="utf-8")' "$producer/.apm/skills/professor-contact/tests/runtime/prompts/issue55-stage3-routing.txt" "$program_root" "$run_dir/eval-prompt.txt"
prompt=$(< "$run_dir/eval-prompt.txt")
command="--json --skip-git-repo-check --sandbox workspace-write --cd '$consumer' --config 'projects={\"$consumer\"={trust_level=\"trusted\"}}' -- '$prompt'"
jq -n --arg command "$command" '{command:$command,timeout:300}' > "$run_dir/eval-request.json"
~~~

R4.4请求已经执行，本段只保留当时的请求准备事实，不再作为当前发送入口。当前正式请求只能采用下文R4.10步骤。R4.4的 `curl` 当时只执行一次；不读取或检查服务进程、配置、数据库或日志。完整响应原样写到 `$run_dir/eval-response.json`；不得启动、停止或重启服务。安装、夹具、提示词或请求构造任一步骤失败时，不发送 `/eval`。完成状态分类后，删除 `$run_dir/consumer`（包括已安装内容和合成程序目录）；保留 `eval-request.json`、`eval-response.json`、HTTP状态及已记录的 `curl` 退出状态、APM版本、`fixture-manifest.json` 和已有运行记录（含产品提交信息），直至结果审核完成。不提交或上传运行目录。

HTTP状态不是200、响应不是有效JSON，或缺少 `.output.thread_id`／`.output.app_server_events` 时，记录为无法判断并停止；非200时不解析响应内容。保留该次请求和响应，不重试。状态结构完整时，按前文“根对话后续命令的具体检查步骤”用 `jq` 读取根线程工具事件和调用结果，再按E组逐项核对实际分支、教授状态、固定写入文件的保存记录和终态后的总览。必要事件、调用或文件不可见的事实记为无法判断；子代理最终消息没有重复完整校验正文不构成缺口。范围内流程目标失败时记业务失败；候选内容失败单独保留，不仅凭 `verdict=fail` 或 `fail_after_2_rounds` 判E组失败，也不为求通过重新采样。按上一段所列运行记录保留所需证据，不提交或上传运行目录。

### 当前关口和结果状态

第三版的必测清单及设计审核仍适用，见[设计审核记录](issue-66-test-plan-review.md)。R4.2、R4.3、R4.4、R4.5和R4.6审核只适用于各自版本。R4.4根据评测环境已使用独立 `CODEX_HOME` 的说明移除 `--ephemeral`，只保留项目可信度配置；这是命令配置修订，不增加A—E目标。R4.4和R4.5请求已完成，R4.5返回HTTP状态504并记为无法判断；不据此判断业务事实，也不重试。R4.6第二关审核已通过。首次准备尝试在APM安装时中断、没有发送请求；用户随后授权重新安装，第二次准备成功并只发送一次 `/eval`。该次E组业务结果为失败：Stage 3在第二轮后以 `fail_after_2_rounds` 终止，存在C10阻塞项；没有进入Stage 4，也没有重抽样。

A—D定向检查共42项全部通过，退出码0，耗时48.039秒。产品代码版本为 `fe1ac16194b3fd0890f02a8a3ad9c623aead5bc4`；完整日志保存在仓库外本次本地运行目录中的 `local-tests.log`，运行目录路径留在本地执行记录中。

R4.3按当时获批步骤发送的一次请求返回HTTP状态200，`curl`退出码0，响应包含根线程及146条应用服务事件，但 `output.child_thread_reads` 为空。根线程发出一次结构化 `spawn_agent` 调用，完成结果为运行时错误 `no rollout found`；没有子线程关系、角色读取或 Stage 3 业务结果。该次E组结果仍记为**无法判断**，不是产品通过或失败。原始请求和响应、状态码、APM版本及合成夹具清单保存在仓库外原运行目录中，具体路径留在本地执行记录中，未纳入提交。

R4.4按第二关通过的修订步骤只发送一次请求，HTTP状态为504，`curl`退出码为0。按步骤，非200结果记为**无法判断**并停止；不据此判断任何Stage 3业务事实，也不重试。请求、原始响应、状态码、APM版本、产品提交及合成夹具清单保存在仓库外的新运行目录中，具体路径留在本地执行记录中，未纳入提交。

### R4.5新增正式运行（E）

仅在专用计划审核代理通过R4.5步骤后，追加发送一次 `/eval`。保留R4.3和R4.4请求、响应及结果，不复用或覆盖运行目录。本次使用新的 `${TMPDIR:-/tmp}/issue66-pr73-eval.XXXXXX` 目录，按上文R4.4完整准备及请求命令执行。产品提交仍为 `fe1ac16194b3fd0890f02a8a3ad9c623aead5bc4`，适配契约仍为 `skills-test-fixtures/codex-eval-adapter@16`，合成资料夹具仍为 `issue55-stage3-pre`；提示词、`--config` 项目可信度设置及其他选项保持与R4.4相同。命令不含 `--ephemeral`，不设置或覆盖 `CODEX_HOME`，只通过 `--config` 配置消费者项目。A—D有效结果复用，不重新运行。

R4.5只有一次 `/eval` 调用，不重试。请求与响应分别保存到新目录的 `eval-request.json` 和 `eval-response.json`，并保存HTTP状态、`curl`退出状态、APM版本、夹具清单和运行记录。按R4.4已审核的规则处理：非200、无效JSON或缺少必要结构时记为无法判断并停止；非200不解析响应内容、不再重发。完成状态分类后删除该目录下的消费者、安装内容和合成程序资料，保留原始请求、原始响应及规定记录至结果审核完成；不得提交或上传临时目录。

R4.5第二关审核通过后只发送一次正式请求，HTTP状态为504，`curl`退出码为0。按计划的非200处理规则，E组仍记为**无法判断**；未检查响应正文，没有业务结论，也未重试。完成状态分类后删除了运行目录中的消费者及其安装内容和合成程序资料；请求、原始响应、APM版本、夹具清单和运行记录保存在仓库外运行目录，具体路径记录在本地执行记录中，未提交。R4.3和R4.4结果保持不变。

### R4.6延长请求等待时间（E）

仅在专用计划审核代理通过R4.6步骤后，追加发送一次 `/eval`。保留R4.3至R4.5的请求、响应及结果，不复用或覆盖运行目录。本次使用新的仓库外运行目录，按R4.5完整准备流程执行，产品提交仍为 `fe1ac16194b3fd0890f02a8a3ad9c623aead5bc4`，适配契约为 `skills-test-fixtures/codex-eval-adapter@16`，合成资料夹具为 `issue55-stage3-pre`；提示词、项目可信度配置、命令和其他选项保持不变，不含 `--ephemeral`，不设置或覆盖 `CODEX_HOME`。A—D有效结果复用，不重新运行。

R4.6只改变请求 JSON 的 `timeout` 字段为1200秒：`jq -n --arg command "$command" '{command:$command,timeout:1200}' > "$run_dir/eval-request.json"`。只发送一次 `/eval`，不重试。请求和原始响应保存在新目录，并记录HTTP状态、`curl`退出状态、APM版本、夹具清单和运行记录。非200不解析响应正文，记为无法判断并停止；其余结果按R4.5相同的结构和E组断言检查。完成状态分类后删除消费者、安装内容和合成程序资料，保留请求、原始响应及规定记录至结果审核完成；不提交或上传运行目录。

R4.6首次准备尝试：APM CLI为 `0.29.0`；远端APM安装停在依赖解析，1110.3秒没有完成且日志未变化，随后被中断并以退出码130结束。夹具生成和提示词准备未开始，没有生成请求文件，也没有发送 `/eval` 请求或产生响应。**这一次准备尝试未执行**，不形成业务结论；其APM版本、安装日志和运行记录保存在仓库外目录，路径见本地执行记录。R4.3至R4.5结果保持不变。

用户授权再次安装后，R4.6在新运行目录成功安装固定产品：APM CLI `0.29.0`，10个依赖，34.5秒。使用原定 `issue55-stage3-pre` 夹具和项目配置，只发送一次 `/eval`；请求 `timeout` 为1200秒，不含 `--ephemeral`，没有设置或覆盖 `CODEX_HOME`。HTTP状态为200，`curl`退出码为0；有效JSON包含计划要求的 `.output.thread_id` 和 `.output.app_server_events`，`.output.exit_code` 为0，`.output.termination_reason` 为 `completed`。响应的 `error`／`stderr`另含 `Reconnecting... 2/5`，但完整输出及 `turn.completed` 均存在。

E组事件记录含2380条应用服务事件及4条子线程读取，角色为两名生成代理和两名校验代理。两次 `stage3-finalize`、两次 `stage3-write-validation`、两轮根线程的准备／保存／记录及一次总览重建均按顺序成功，退出码均为0。第一轮记录 `needs_correction=true`、`terminal=false`；第二轮记录 `needs_correction=false`、`terminal=true`。最终状态文件的 `validator.results.DIR00001` 记为 `fail_after_2_rounds`，有一项C10阻塞问题，位置为“候选1、2、3红线”；E组Stage 3业务结果按计划记为**业务失败**，不重抽样。Stage 3状态、候选稿和总览均已写入；Stage 4的 `套磁选择.json`、`邮件输入.json` 不存在。三份Stage 2输入的SHA-256仍与夹具清单一致。

校验子线程的最终消息正文只以 `encrypted_content` 提供，且子线程读取没有包含 `turns`；因此无法把完整最终正文与固定写入文件逐字比较。该项按计划单独记为**无法判断**，没有用记录状态反推正文一致。

本次请求、原始响应、APM版本及安装日志、夹具清单和运行记录保存在仓库外目录 `/var/folders/1y/9709mm1s6115w3fbssy9162h0000gn/T/issue66-pr73-eval.u4Mk6M`；原始响应文件为 `eval-response.json`。评测消费者已在完成分类后删除，运行证据不提交到仓库。R4.3至R4.5历史结果保持不变。版本为 `issue-66-test-plan-new-rules-r4.6-2026-10-09`。

### R4.7通过条件澄清与结果交接

用户在分析R4.6结果后确认：E组应分别判断本次流程目标与候选内容结论。本版只澄清这一条件，A—D目标和有效结果、E组输入、配置、检查方法及所有正式尝试保持原归属，不安排新的模型请求。

上文R4.6将C10内容失败直接记为E组业务失败，是当时的原分类，作为历史记录保留；它不能单独作为R4.7下的E组失败依据。候选内容两轮失败的事实不变，红线修改限制和重复红线问题仍须如实报告。本版不改产品红线保护或多个候选问题的识别规则，不将这些已有问题加入必测范围。

本地测试工程师已用R4.6保存的原始响应和仍在仓库外的两份固定写入文件按本版E组观察点复核，没有发送新请求。原始事件流中的 `rawResponseItem/completed` 事件含两轮校验子线程完整的最终正文，事件序号分别为 `34275` 和 `35235`；子线程读取包装中的 `turns` 为空，不影响从原始事件读取正文。

两轮 `stage3-write-validation` 的成功标准输出与对应 `validator-output.json` 均逐字节相同。两轮校验子线程最终正文与对应文件均不相同：正文各少一个末尾换行符，补上该换行符后才与文件完全相同。计划要求按原字符比较且不得修整空白，因此E组最终正文比较为**失败**，不再记为无法判断。

其余可观察流程步骤均按顺序成功：生成及校验子线程职责与教授匹配；根使用同一调用凭据完成准备、保存和记录；第一轮记录触发仅涉及 `DIR00001` 的一次修正；第二轮记录 `terminal=true`、`fail_after_2_rounds` 后停止，没有第三轮，并在终态后重建一次总览。E组流程结论为**失败**，原因是上述末尾换行不一致。候选内容结论单独记录为两轮后仍有一项C10阻塞问题；这项内容失败本身不反转流程结论。R4.6原分类保留为历史，不重新采样，不进入Stage 4。本次复核不批准第三关口或合并。

### R4.8唯一原文调整及既有结果复核

验收决定人于2026年10月9日确认，校验文件是唯一正式校验原文；校验子代理最终消息只报告固定写入结果，不再要求重复完整 JSON，也不与文件逐字节比较。本版据此修改D、E组检查方法，删除R4.7中由末尾换行造成的失败条件。JSON对象输入与固定写入文件使用标准 `jq` 结构相等判断；固定写入输出与文件、源文件与保存文件继续按逐字节相同检查；保存与记录之间继续采用产品已有摘要绑定。

本地测试工程师复用R4.6原始响应、两份固定写入文件及R4.7已经取得的观察，不发送新请求。该证据继续证明两轮固定写入成功、标准输出与指定文件逐字节相同、根随后保存并记录同一文件，以及生成、修正、停止和总览顺序。它也没有显示根从子代理最终消息重建校验文件。这些未变事实可以复用。

两轮旧子代理最终消息各少一个末尾换行符的事实继续保留，但它只说明旧消息载体与文件排版不同，不再属于新版失败条件。旧响应仍返回完整校验 JSON，不能证明第十六版规定的完成报告字段及“不含校验正文”；因此R4.8的E组结果记为**尚未执行**，不得由旧证据改判通过。候选内容的历史结论仍为 `fail_after_2_rounds`，剩余一项C10阻塞问题。A—D的42项有效通过结果继续复用。产品实现负责人须先按第十六版执行计划同步校验代理、Codex流程及实际安装内容；同步后只运行一次当前实现的E组，不重跑A—D。本记录不批准第三关口或合并。

### R4.10：完成报告检查、端口接线修正及同步后运行步骤

日期：2026年10月9日。目标仍为第十六版完整执行计划规定的 Codex 流程。R4.9新增的定向检查位于 `.apm/skills/professor-contact/tests/test_issue66_validator_report_contract.py`，覆盖成功报告、失败报告、缺省原因码、禁止把校验正文放进完成报告，以及未传 `output_file` 时保留旧只读返回。测试默认读取生产者代理源文件；设置 `PROFESSOR_CONTACT_VALIDATOR_AGENT` 后，会直接读取指定的 Codex 安装件 `.toml` 文件中的 `developer_instructions`。R4.10只修正评测端口接线，不增加A—E目标或正式请求次数。

R4.9复核的 PR 提交为 `b4c6f46537241cb062c7088989adbd07f30553fb`。在 `.apm/skills/professor-contact/tests` 运行 `UV_CACHE_DIR=/private/tmp/issue66-validator-report-uv-cache uv run --python 3.12 --no-project python -B -m unittest test_issue66_validator_report_contract -v`，结果为3项中1项通过、2项失败，退出码1：旧只读返回兼容通过；新成功／失败完成报告和缺省 `validation_write_failed` 检查失败。失败原因是该代理源文件未包含第十六版的新报告格式及缺省原因码，不是测试启动错误。故该旧提交不是可安装的E组目标；未安装旧产品，也未发送 `/eval`。后续产品候选 `6aa2c8b23f9a723fff1b862851eb49b72a4c9a1d` 尚未由本地测试工程师执行下列源文件与安装件检查，不能预先视为有效E组目标。

产品实现负责人将技能流程、校验代理及其 Codex 安装内容按第十六版同步并推送后，执行人须先核对源文件定向检查通过，并记录当时实际、干净且已推送的产品提交 SHA。下列源检查、安装、夹具和请求文件准备步骤从生产者仓库根目录开始执行。该 SHA 写入运行记录，之后 APM 安装固定使用同一 SHA；不使用分支名、移动标签或本地路径。源文件检查失败时立即停止，不安装、不发送请求。

```sh
set -eu
set -o pipefail
producer=$(pwd)
run_dir=$(mktemp -d "${TMPDIR:-/tmp}/issue66-pr73-r410.XXXXXX")
consumer="$run_dir/consumer"
git -C "$producer" status --porcelain > "$run_dir/producer-status.txt"
test ! -s "$run_dir/producer-status.txt" || exit 1
product_sha=$(git -C "$producer" rev-parse HEAD)
printf '%s\n' "$product_sha" > "$run_dir/product-sha.txt"
cd "$producer/.apm/skills/professor-contact/tests"
if UV_CACHE_DIR="$run_dir/uv-cache" uv run --python 3.12 --no-project python -B -m unittest \
  test_issue66_validator_report_contract -v 2>&1 | tee "$run_dir/source-contract-tests.log"; then
  test_exit=0
else
  test_exit=$?
fi
printf '%s\n' "$test_exit" > "$run_dir/source-contract-tests.exit"
test "$test_exit" -eq 0 || exit 1
```

源文件检查成功后，再从干净消费者经受支持的 APM 路径安装该 SHA，并对实际安装的 Codex 代理文件运行同一组检查。安装失败、安装件缺失、定向检查失败或退出码非0时立即停止，不发送 `/eval`。

```sh
set -eu
set -o pipefail
mkdir -p "$consumer"
cd "$consumer"
apm --version > "$run_dir/apm-version.txt"
apm install "ScholarWorkflow/professor-contact#$product_sha" --target codex > "$run_dir/apm-install.log" 2>&1
validator_agent="$consumer/.codex/agents/professor-contact-style-validator.toml"
test -f "$validator_agent" || exit 1
cd "$producer/.apm/skills/professor-contact/tests"
if PROFESSOR_CONTACT_VALIDATOR_AGENT="$validator_agent" \
  UV_CACHE_DIR="$run_dir/uv-cache" uv run --python 3.12 --no-project python -B -m unittest \
  test_issue66_validator_report_contract -v 2>&1 | tee "$run_dir/installed-contract-tests.log"; then
  test_exit=0
else
  test_exit=$?
fi
printf '%s\n' "$test_exit" > "$run_dir/installed-contract-tests.exit"
test "$test_exit" -eq 0 || exit 1
```

安装件检查通过后，复用R4.6已审核的 `issue55-stage3-pre` 合成夹具、提示词、项目配置、评估服务连接及事件检查步骤。准备与请求完整命令如下；产品 SHA 仍取上述记录值，`timeout` 固定为1200秒。任何准备步骤失败都不得发送请求。

```sh
set -eu
set -o pipefail
program_root="$consumer/fixture-program"
UV_CACHE_DIR="$run_dir/uv-cache" uv run --python 3.12 --no-project python \
  "$producer/.apm/skills/professor-contact/tests/runtime/prepare_issue55_stage3_fixture.py" \
  --program-root "$program_root" \
  --output "$run_dir/fixture-manifest.json" > "$run_dir/fixture-build.json" 2>&1
test -s "$run_dir/fixture-manifest.json"
UV_CACHE_DIR="$run_dir/uv-cache" uv run --python 3.12 --no-project python -c 'import sys; from pathlib import Path; template=Path(sys.argv[1]).read_text(encoding="utf-8"); root=sys.argv[2]; assert template.count("{{PROGRAM_ROOT}}") == 1; Path(sys.argv[3]).write_text(template.replace("{{PROGRAM_ROOT}}", root), encoding="utf-8")' \
  "$producer/.apm/skills/professor-contact/tests/runtime/prompts/issue55-stage3-routing.txt" \
  "$program_root" "$run_dir/eval-prompt.txt"
test -s "$run_dir/eval-prompt.txt"
prompt=$(< "$run_dir/eval-prompt.txt")
command="--json --skip-git-repo-check --sandbox workspace-write --cd '$consumer' --config 'projects={\"$consumer\"={trust_level=\"trusted\"}}' -- '$prompt'"
jq -n --arg command "$command" '{command:$command,timeout:1200}' > "$run_dir/eval-request.json"
jq -e '.timeout == 1200 and (.command | type == "string" and length > 0)' "$run_dir/eval-request.json" > /dev/null
```

保留上述 shell 中绝对路径形式的 `run_dir`，然后在已配置的评测服务工作区根目录执行以下正式请求块；此时 `.` 就是评测服务工作区。真实的 `curl` 必须由 `direnv exec .` 直接执行，使 `EVAL_PORT` 只在该命令环境中取得。不得新增评测服务路径变量，也不得在请求外读取、保存或探测端口。缺少 `direnv`、`curl` 或有效 `EVAL_PORT` 时，该次真实请求命令直接失败并记录退出状态。

```sh
curl_exit=0
http_status=$(direnv exec . sh -c '
  set -eu
  case "${EVAL_PORT:-}" in
    ""|*[!0-9]*) exit 1 ;;
  esac
  curl --silent --show-error --output "$1" --write-out "%{http_code}" \
    -H "Content-Type: application/json" --data-binary @"$2" \
    "http://127.0.0.1:${EVAL_PORT}/eval"
' issue66-r410-eval "$run_dir/eval-response.json" "$run_dir/eval-request.json") || curl_exit=$?
printf '%s\n' "$http_status" > "$run_dir/http-status.txt"
printf '%s\n' "$curl_exit" > "$run_dir/curl-exit.txt"
```

R4.10的 `curl` 只执行一次。HTTP状态非200、响应不是有效JSON或必要字段缺失时记为无法判断，不重试。状态结构完整时，按“根对话后续命令的具体检查步骤”及E组清单核对实际分支、完成报告、固定写入文件、保存与记录及最终教授状态。完成分类后删除 `$run_dir/consumer`；运行目录保留请求、原始响应、安装版本与日志、产品 SHA、定向测试日志、夹具清单、状态码和运行记录，不提交或上传。产品提交 SHA 的实际记录、源文件与安装件检查结果及唯一一次请求结果待本地测试工程师补录；在此之前E组仍为**尚未执行**，不批准第三关口或合并。
