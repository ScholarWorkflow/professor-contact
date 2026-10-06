# 第72号拉取请求完整待审测试执行记录第30版

记录编号：`issue68-r30-r25-full-procedure-2026-10-06`。本文完整取代第29版记录；旧版仅留作历史，不需要拼接旧评论。角色为本地测试工程师。**第二关口尚未完整通过，正式 PC68-R1 未执行**。

## 1. 权威来源与版本

| 项目 | 固定来源与版本 |
| --- | --- |
| 冻结验收 | `issue-68-gate1-r4-2026-10-05`，[第68号议题第四版](https://github.com/ScholarWorkflow/professor-contact/issues/68#issuecomment-5981562292)，决定人为 `RekiDunois` |
| 获批产品计划 | `issue-68-plan-r13-2026-10-06`，[第十三版](https://github.com/ScholarWorkflow/professor-contact/issues/68#issuecomment-6000673923)，[范围批准](https://github.com/ScholarWorkflow/professor-contact/pull/72#issuecomment-6000931583) |
| 唯一完整测试计划 | `issue-68-test-plan-r25-2026-10-06`，[第二十五版](https://github.com/ScholarWorkflow/professor-contact/pull/72#issuecomment-6010481027)，完整取代第二十四版 |
| 目标产品 | `b39a4252e3ce473f8cdeedd2e12b0cf86d6f597d` |
| 共享测试资产 | `c738fa2f8bcbb16cd99d741332d5f59b062b6357` |
| 本轮测试实现基线 | `ffefc7e`；候选为包含本文及第30版改动的固定提交，由审核者指定，不能引用不存在的自指提交 |
| 证据约定 | `tests/runtime/issue68-runtime-evidence-contract-r19.json`，修订 `issue-68-runtime-evidence-r30-2026-10-06` |
| 规则 | 项目父目录的 `PROJECT_CONSENSUS.md`、`Test Engineer Rule.md`、`Plan Reviewer Rule.md` 当前文本；冲突以前者为准 |

本文所有仓库内路径以 `.apm/skills/professor-contact/` 为前缀。产品不修改；不重开验收和产品计划。仅补测试观察、判定、预检与完整步骤。独立工作树为 `/private/tmp/worktrees/pc68-r30`。

## 2. 用例与证明负责者

正式用例只有 `PC68-D1` 和 `PC68-R1`。姓名假定唯一，同名支持及测试不在范围内。第五阶段本地来源、指定邮件、同教授整批、教授隔离、只读发现、分配与原值保持由下表负责；不增加前四阶段、历史迁移、写锁、文案与业务校验要求。

| 要求 | 证明负责者及事实 |
| --- | --- |
| R68-1、R68-6 | D1/P1：显式本地包唯一来源，无全局回退、双读写或第二迁移 |
| R68-2、R68-7 | D1/P2：目标限定、自身非法拒绝、无关噪声不阻断、仅处理当前教授输出 |
| R68-3 | D1/P3：同教授整批、失败零部分提交 |
| R68-4、R68-7 | D1/P4：乙失败不回滚甲；R1：真实逐教授委派与独立结果消费 |
| R68-5 | D1/P5：独立总览及人工保护；AD68-2通用写锁归第48号议题，不新增本议题证明 |
| AD68-3 | D1/P6：只读逐包发现、坏包隔离 |
| R68-8、AD68-4、AD68-5 | D1/P7：确定性分配、归属、原值与后续选择读取及包装；R1：本次根分配→实际教授交接→首次计划业务数据、临时文件清理 |
| AD68-1 | R1：分别委派、等待、消费后独立一次总览及原样报告 |

R1固定为缺核验前提。已经发生的分配、读取、首次计划、结果消费及总览须直接证明；不得要求或宣称尚未发生的后续选择读取、渲染、提交和校验。后续选择读取由D1/P7承担。

## 3. 完整输入、允许变量和实现文件

输入由固定 `tests/runtime/prepare_issue68_stage5_routing.py` 的 `EXPECTED_OWNERS` 和 `test_contact_state.write_issue59_stage5_fixture` 生成，不由执行者猜内容，不从根分配输出反推预期。两位教授为 `試験 教授`、`佐藤 花子`，编号分别为 `試験 教授::DIR00001::DIR00001_1`、`佐藤 花子::DIR00001::DIR00001_1`；每份独立选择保留 `first_choice=false`、`signature_name=試験 太郎`、`learning=比較手法の基礎知識の習得`，以及各自 `transport_sentinel=owner-0/owner-1`。完整原始选择另有 `email_id=unselected::D::I`、`transport_sentinel=noise` 的无关行。坏包由 `ISSUE59_MALFORMED_JSON` 写入 `教授研究/Z分野/无效样例`。两位教授证据为 `none`、核验为 `missing`；模板、原始结果、包及状态由固定准备程序写出。

准备程序只检查本例核验前提并生成独立预期，不生成根代理交接或分教授选择包，不替根代理分配。其 `fixture-manifest.json` 归档教授目录、包、编号、全部选择、首次计划业务数据、预期结果、坏包路径及执行前文件摘要；`canonical-choices.json` 保存完整原始输入，`root-prompt.txt` 保存实际请求。输入字节与初始状态以该固定程序及本次归档为唯一来源。

`PC68_PRODUCT_ROOT` 为干净产品检出目录，`PC68_SHARED_ROOT` 为固定共享资产的干净检出目录，`PC68_EVAL_ROOT` 为现有评估服务检出目录；先在各目录执行 `pwd` 取得绝对路径，保留到本次本地原始执行记录，再赋值，不在公共证据中泄露用户路径。`PC68_OUTPUT_ROOT` 为新建正式运行编号对应的空目录；`PC68_PREFLIGHT_ROOT` 为 `/private/tmp/` 下新的预检输出目录，不能使用已存在的第01或第02目录覆盖旧证据。

允许变量只有：产品检出绝对路径、共享检出绝对路径、评估服务检出绝对路径、全新且不相交的输出目录与运行编号、缓存目录。这些由操作系统实际目录与服务 `direnv` 得到，执行前归档原值。产品与共享提交、输入内容、提示词、模型、执行器、观察程序、沙箱、入口和判定不得临场替换。默认模型依项目共识及固定请求构造器为 `gpt-6-luna`、`model_reasoning_effort=low`，保存本次请求中的实际值；端口由既有服务读取，不自行分配或启停服务。

| 文件 | 职责 |
| --- | --- |
| `tests/runtime/preflight_issue68_environment_r30.py` | 关口前支持安装、只读服务隔离、单次纯合成评估请求；没有教授业务、分配和委派 |
| `tests/runtime/preflight_issue68_synthetic_observation_r30.py` | 仅空白消费者单次合成普通命令观察；当前支持安装缺口不由此程序填补 |
| `tests/runtime/preflight_issue68_lifecycle_observation_r30.py` | 单次纯合成创建、实际读取、删除的有限根命令能力检查；不执行教授业务 |
| `tests/runtime/test_preflight_issue68_environment_r30.py` | 环境预检解析的合法及反例验证 |
| `tests/runtime/capture_issue68_owner_stage5_plan_r1.py` | 正常交接单次解析，只读复制同一个对象，调用原已安装计划程序，保存实际参数与原始输出 |
| `tests/runtime/verify_issue68_stage5_routing_r19.py` | 完整分配包/目标/选择→真实解析对象→实际首次调用及业务数据核对 |
| `tests/runtime/run_issue68_stage5_routing_r19_codex.py` | 正式单次评估入口、版本/隔离检查、运行证据和判定 |
| `tests/runtime/issue68_lifecycle.py` | 正式请求前后文件快照、同次真实事件的有限解析及创建→读取→清理关系核对；没有独立业务入口 |
| `tests/test_issue68_lifecycle.py` | 生命周期完整合法链、产品违约、缺失及归属损坏的合成验证 |
| `tests/test_issue68_lifecycle_integration.py` | 请求边界及原始事件重建检查，包含不替换业务解析或生命周期判定的5项完整组成入口样例 |
| `tests/runtime/run_issue68_stage5_routing_r19.py` | 原流程接线，使用固定共享资产 |
| `tests/runtime/prompts/issue68-stage5-root.txt` | 只保留业务任务及只读观察安排，不教学分配结果或教授工作步骤 |
| `tests/test_issue68_runtime_r19.py` | 独立已知输入的判定正例、产品失败和无效/阻断反例 |

## 4. 关口前最小预检与命令

按测试规则第3.2节，安装、服务隔离、普通命令输出和判定验证在第二关口完整通过前完成。它们不运行完整教授业务，不生成正式验收结论。第29版把这些检查推迟到关口后的循环门已删除。正式执行器仍保留关口门；关口前使用专门预检入口，不修改正式门来运行业务。

在上述独立测试工作树执行：

```sh
UV_CACHE_DIR=/private/tmp/pc68-r30-uv-cache uv run --no-project python .apm/skills/professor-contact/tests/runtime/preflight_issue68_environment_r30.py \
  --producer-root "$PC68_PRODUCT_ROOT" \
  --fixture-root "$PC68_SHARED_ROOT" \
  --eval-direnv-root "$PC68_EVAL_ROOT" \
  --output-dir "$PC68_PREFLIGHT_ROOT"
```

只使用全新输出目录。预检先核实两个固定提交与服务干净版本/隔离，再通过 `apm install https://github.com/ScholarWorkflow/professor-contact.git#b39a4252e3ce473f8cdeedd2e12b0cf86d6f597d --target codex --trust-transitive-mcp` 在隔离消费者安装，核对安装入口摘要及 `--help`。接着只发一次合成命令请求：单次读取合成JSON、从同一解析对象启动回显子进程，保留未改写对象；不读取教授包、不执行教授业务、不委派、不启动/停止/重启服务。命令事件须按运行代次、当前根线程/轮次、调用编号及开始/结束顺序唯一关联；解析 `aggregatedOutput` 验证实际读取和同对象转交。

保存 `preflight-result.json`、`service.before/after.json`、`tool-versions.json`、`install/command.json` 和安装/帮助完整日志、`synthetic-manifest.json`、合成输入与两份脚本、`prompt.txt`、`request.json`、`response.json`、`observation.json`、`integrity.json`。只有 `PRECHECK_READY` 加完整证据才表示该最小检查就绪；任何未完成结果记录具体停止原因，不是正式用例终态或第二关口批准。请求超时不重发，保留原始尝试。

第03次仅合成观察的固定来源为 `tests/runtime/preflight_issue68_synthetic_observation_r30.py`，从原始执行源原样纳入，不改写执行字节。要复查此独立预检，只使用 `/private/tmp/` 下不存在的新目录，先用 `mkdir` 创建该目录，再运行下列命令；`PC68_SYNTHETIC_ROOT` 与其他目录不相交，`PC68_RUNTIME_ROOT` 为本测试提交的 `tests/runtime` 绝对路径，按 `pwd` 取得并保留。该命令不再次安装，不表示整个预检已完成。

```sh
mkdir "$PC68_SYNTHETIC_ROOT"
UV_CACHE_DIR=/private/tmp/pc68-r30-uv-cache uv run --no-project python .apm/skills/professor-contact/tests/runtime/preflight_issue68_synthetic_observation_r30.py \
  "$PC68_RUNTIME_ROOT" "$PC68_SYNTHETIC_ROOT" "$PC68_EVAL_ROOT"
```

| 必要预检 | 本版固定检查与依据 |
| --- | --- |
| 入口可执行 | 固定产品支持安装、安装入口摘要与帮助退出码；共享资产正式请求构造器和项目共识指定配置 |
| 环境隔离 | 既有服务测试存储及进程只读前后记录；消费者安装树、输入摘要和全新独占输出 |
| 事实可观察及归属 | 普通命令真实输出单次解析对象并转交，与当次运行、线程、轮次、调用及事件顺序唯一关联；正式线程与最终结果仍用固定共享适配器的已有正式约定，不用合成请求创造教授关系 |
| 判定能区分结果 | 第25版独立预期及正反例验证，含完整分配包/目标/选择、已清理输入、错误首次业务、缺失、损坏及核验早停；相同程序含义共用一次检查，不重复完整业务 |

判定验证固定命令：

```sh
UV_CACHE_DIR=/private/tmp/pc68-r30-uv-cache uv run --no-project python -m unittest discover -s .apm/skills/professor-contact/tests -p test_issue68_runtime_r19.py
UV_CACHE_DIR=/private/tmp/pc68-r30-uv-cache uv run --no-project python -m unittest discover -s .apm/skills/professor-contact/tests/runtime -p test_preflight_issue68_environment_r30.py
jq -e . .apm/skills/professor-contact/tests/runtime/issue68-runtime-evidence-contract-r19.json
```

本轮合成检查归档为 `tests/runtime/evidence/issue68-r30-precheck-validation.json`：`test_issue68_runtime_r19.py` 34项通过（最终4.419秒）；`test_issue68_runtime_recipe.py` 11项通过；环境预检12项通过；相邻 `test_issue68_runtime_r18.py` 20项通过（0.031秒）；共77项，4个命令均退出0。归档含前三份完整标准输出及相邻检查真实工具结果摘要。第30版契约文字更新后一条旧描述断言曾失败，修正为当前两段语义后重新检查34项通过；这不是产品失败或正式执行。它们只验证测试程序，不是D1或R1的正式执行。

第30版候选 `579dd34` 固定后，只读审核发现两项判定缺陷：真实服务的运行代次为JSON整数，旧判定只接受历史字符串；已由根调用直接证明的违规可能被缺少教授观察遮蔽。修正后整数和历史字符串均合法，但调用、事件及当前输出须同时满足值和类型严格相同，不接受布尔值或类型转换。独立根调用的有效违规证据先行判定，不因教授缺观察或回执降级。新增反例检查首次38项中4项失败，修正后38项通过、退出0，耗时5.914秒。原 `/private/tmp/pc68-r30-attribution-before.log`、`/private/tmp/pc68-r30-attribution-after.log` 被后续边界检查误覆盖；已从原工具输出恢复可见末65行/末8行，分别保存在 `/private/tmp/pc68-r30-attribution-generation-before.log`、`/private/tmp/pc68-r30-attribution-generation-after.log`。恢复来源说明为 `/private/tmp/pc68-r30-attribution-generation-recovery-source.txt`；工具窗口之外的原始输出无法恢复，不称完整原始日志，不通过重跑冒充原轮次。

边界检查另用独有文件保留三轮完整输出：`/private/tmp/pc68-r30-attribution-boundaries-before.log` 为27项、4项失败；`/private/tmp/pc68-r30-attribution-boundaries-after.log` 为42项通过、6.564秒；`/private/tmp/pc68-r30-attribution-boundaries-final.log` 为45项通过、8.351秒。各轮计数是当轮检查，不相加成唯一组件数量。第6节同步删除逐教授六种测试终态及无产品失败时总体留空的额外承诺，恢复第二十五版要求的逐教授真实业务结果和整例验收分类。各轮输出及恢复范围归档为 `tests/runtime/evidence/issue68-r30-review-fixes-validation.json`，这些修正仍属待审测试实现，不是正式用例执行或第二关口批准。

顶层最终关联检查使用离线模式：环境判定12项通过、准备及步骤检查11项通过，均退出0；完整输出 `/private/tmp/pc68-r30-environment-final-check.log`、`/private/tmp/pc68-r30-recipe-final-check.log` 同时归档到上述修正证据。这是当前程序核对，不增加正式用例或唯一组件数量。

读取后清理仍能接受合法证据；实际包/目标/完整选择与前序不符、实际首调错包/改编号/兄弟业务数据必须判产品失败；正确值仅在命令字面量、打印预期值、无关读取或事后读取不能通过。缺失与损坏/归属冲突分别保留阻断及无效分类。合法核验不足接受已发生的首次包读取与业务任务，不要求后续选择消费。合成样例的预期来自第二十五版计划，不能由判定程序反推。

### 本轮实际预检记录

第01次预检已结束，脚本退出码1，状态为 `PREFLIGHT_INCOMPLETE`、原因 `supported_install_failed`。支持安装在240秒保护窗口耗尽后退出124；日志记录解析8项依赖，没有据此证明产品错误。原始材料保留在 `/private/tmp/pc68-r30-environment-preflight-01`，可访问脱敏摘要为 `tests/runtime/evidence/issue68-r30-environment-preflight-01.json`。已取得固定产品/共享干净版本与既有服务实例/测试存储只读隔离证据，服务版本为 `3fdfa9387140cfc2e2aa3af415f85015f79706d2`。该版本取自当次服务，不是计划冻结服务版本。

第02次使用同一支持安装路径，安装保护窗口由旧240秒增加到600秒，是预检修订后的新尝试。该次亦已结束，安装超时退出124，预检状态 `PREFLIGHT_INCOMPLETE`、原因 `supported_install_failed`；标准错误为空，日志仍仅解析8项依赖。原始输出保留在 `/private/tmp/pc68-r30-environment-preflight-02`，可访问脱敏证据为 `tests/runtime/evidence/issue68-r30-environment-preflight-02.json`。没有完成安装入口或帮助检查，没有发送合成评估请求，没有正式执行；不覆盖或改判第01次。

因此支持安装的入口可执行性仍有明确缺口，不能标本角色全部完成或第二关口齐备。环境预检判定反例12项通过，日志 `/private/tmp/pc68-r30-preflight-unit-checks.log`。第03次仅用空白隔离消费者执行一次纯合成普通命令请求，跳过再次安装，已退出0、状态 `SYNTHETIC_OBSERVATION_READY`。实际命令开始/结束事件序号为22328/22329、运行代次1；输出实际单次解析对象并由同一对象转交，保留选择 `[2,1,2]`、原值 `原编号::空 格`，子进程退出0。输入及两份脚本摘要前后相同，消费者保持空白、服务实例及测试存储相同。原始目录 `/private/tmp/pc68-r30-synthetic-observation-03`，可访问证据为 `tests/runtime/evidence/issue68-r30-synthetic-observation-03.json`。该脱敏投影保留原始材料的摘要与来源位置，完整响应仍在本地，不能用投影重建没有发生的正式事件。实际请求为 `gpt-6-luna`、推理强度 `low`，服务实际执行工具版本 `codex-cli 0.159.0-alpha.12.1`，与本地准备工具 `codex-cli 0.160.1` 分别记录；服务内部最终解析的模型未公开，不宣称已取得该值。此项只证明现有服务输出与调用关联能力，不替代支持安装、安装入口摘要与帮助检查，也没有教授业务或正式验收；总体预检仍为 `PREFLIGHT_INCOMPLETE`。

## 5. 正式 PC68-R1 固定步骤

第二关口审核者指定包含本文的唯一完整固定提交，并明确完整通过与正式许可后，才允许正式入口调用。现有契约保持 `second_gate_status=INCOMPLETE`、`formal_run_allowed=false`；本地测试工程师不自行改为通过。正式消费者与输出另建，不能复用合成预检消费者。

工作目录为获批测试提交所在的仓库根目录，使用固定命令；下列大写变量按第3节实际目录取值，先保存到本次执行记录：

```sh
UV_CACHE_DIR=/private/tmp/pc68-r30-uv-cache uv run --no-project python .apm/skills/professor-contact/tests/runtime/run_issue68_stage5_routing_r19_codex.py \
  --producer-root "$PC68_PRODUCT_ROOT" --producer-sha b39a4252e3ce473f8cdeedd2e12b0cf86d6f597d \
  --fixture-root "$PC68_SHARED_ROOT" --fixture-sha c738fa2f8bcbb16cd99d741332d5f59b062b6357 \
  --eval-direnv-root "$PC68_EVAL_ROOT" --output-dir "$PC68_OUTPUT_ROOT"
```

启动边界是正式运行器完成版本、干净消费者安装、输入与输出隔离、六项环境证据及观察检查后，写入本次启动记录并发送唯一正式请求。边界前失败是 `CASE_NOT_STARTED`。正式请求一旦发送，不换模型、不重试、不另发评估请求代替委派。

六项实际事实来源：`model`取本次请求；`executor`取实际编码执行分支的函数/模块和源文件摘要；`entrypoint`取已安装 `contact_state.py` 路径/摘要；`isolation`取服务与存储前后快照；`shared_assets`取固定产品/共享干净提交及锁文件摘要；`service_version`取本次只读服务干净提交并前后比较。监听进程只作服务来源，不能冒充执行器。预检记录验证来源可用，正式请求仍重新保存本次实值到 `runtime-environment-evidence.json`、`input-evidence-preflight.json`、`provenance.json`，不拿旧预检替代本次记录。


步骤按表中顺序执行。任何前置门未通过即停止，不得跳到下一步。PC68-R1 只允许一次正式服务请求，不重试，不更换模型、执行器、服务或入口来寻找成功。

| 步骤 | 操作和实际输入来源 | 必须保存的直接证据及核对条件 | 停止条件 |
| --- | --- | --- | --- |
| 0. 冻结与准入 | 使用唯一完整测试实现版本、获批产品目标和 r25 完整记录；完成第二关口审核及第 4 节最小观察预检 | 审核指定版本、产品与测试完整 SHA、入口及判定程序版本；确认正式入口类别未改，产品代码未为测试修改 | 第二关口未完成时先记 `CASE_NOT_STARTED`，仅禁止正式业务请求；候选 SHA 未固定、预检不通过或任一必填事实未知时也不启动 PC68-R1。当前状态即为此门未通过 |
| 1. 准备输入 | 建立两位教授独立本地包、合法显式选择、无关行、坏包与缺核验状态；保存独立预期。不得提前分配、拆分选择或制作教授交接文件 | 每个原始输入的来源、路径、内容校验值；教授目录和邮件编号原值；本地状态及隔离目录的执行前快照；输入之间不重叠的证据 | 输入不完整、预期并非独立于被测输出、目标或目录冲突、准备阶段写入根代理交接/分配结果：停止并修复测试准备，不运行正式请求 |
| 2. 检查安装和隔离 | 按固定产品提交支持的安装方式建立干净消费者（关口前最小安装已由独立预检检查；正式运行仍新建消费者）；记录其 `contact_state.py` 路径和哈希；记录 Codex dispatch 身份及源文件哈希；通过只读请求前快照记录服务版本和隔离；检查空输出目录 | 产品及消费者版本、安装入口路径和哈希；dispatch 函数/模块身份与 dispatcher/runner SHA-256；目录为空且彼此不重叠；服务请求前 provenance 快照 | 关口前可以经独立预检入口只读检查服务及支持安装；正式请求仍须第二关口完整通过；安装失败、产品版本不符、目录不干净或隔离不成立：`CASE_NOT_STARTED`；不得直接运行命令行工具替代入口，也不得启动或重启评估服务 |
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

根事件须绑定当前根轮次；正式教授的调用开始/完成事件则须具备彼此相同且非空的自身轮次、正式根子关系和相同运行代次，不要求教授轮次等于根轮次。非正式关系不能提供教授证据。子线程轮次边界检查新增反例首次2项中1项失败；修正后46项通过，随后47项通过，修正非正式关系样例后最终仍47项通过。完整输出分别为 `/private/tmp/pc68-r30-attribution-child-turn-before.log`、`/private/tmp/pc68-r30-attribution-child-turn-after.log`、`/private/tmp/pc68-r30-attribution-child-turn-final.log`、`/private/tmp/pc68-r30-attribution-child-turn-final2.log`，各轮分别归档，不叠加计数。

### 文件生命周期的固定收集与当前缺口

正式生命周期收集没有独立业务命令。上述正式运行器在实际发送请求前调用 `issue68_lifecycle.collect_before(manifest, consumer)`，保存 `codex/lifecycle.before.json`；判定前调用 `collect_lifecycle(before, manifest, consumer, response, input_verifier)`，保存 `codex/lifecycle-evidence.json` 并写入 `fixture-manifest.json` 的 `lifecycle_evidence`。前后边界通过运行编号、请求/响应摘要、递增时刻及保存的请求和前置快照关联。异常退出也保留能够收集的后置材料。正式判定必需调用 `verify_bound_lifecycle(evidence, manifest, response, adapter, input_verifier)`：它从原始事件重新构建读取、分配及操作事实，核对归属与账本一致，再调用 `verify_lifecycle` 核对文件链；缺生命周期证据不能通过。它不生成教授交接、不替代理清理，也不调用产品业务。独立已经确证的产品失败仍保留，不被其他证据缺口遮蔽。

证据含程序输入区及消费者的完整前后文件快照、文件摘要/字节数、符号链接目标和缺席；同次教授捕获记录关联实际读取路径、摘要、正式线程、调用编号、运行代次及顺序。准备程序写入一份被动的其他请求合成文件，列入保护基线 `protected_other_request_files`，它在正式请求开始前已经存在；不启动第二次请求或新增并发完整业务。实际根分配的完整返回保留 `choices_path`、`out_path`；已安装固定产品成功调用 `stage5-partition-choices --out` 的真实返回与源码“先写文件再输出”路径用于确认分配文件创建，不能用命令中的JSON内容充当实际输入。传递文件仍必须具备根实际创建、对应教授实际读取和真实清理的可归属链。

有限操作解析只识别实际完成且退出码为JSON整数0的根命令中的明确绝对路径写入（`printf`/`cat` 重定向）、读取（`cat`）及删除（`rm`/`unlink`）；不执行任意代码，不从未知脚本推断副作用。清理成功事件须晚于对应读取，并结合最终缺席、教授状态与输出未改变、已有其他请求文件字节不变检查。只看到运行后文件缺席或文件不变不能证明创建→读取→清理已经发生。只核对本次实际用于传递的路径：原选择、教授交接以及实际采用的分配输出文件；根代理可直接消费分配的真实标准输出，不强制再用 `cat` 读取整份输出文件或添加业务动作。完整有效链才认可此项；实际改写、残留或错删为产品失败，归属矛盾或证据损坏为无效，缺创建、实际读取或清理证据为观察阻断。

生命周期首轮合成验证19项通过、退出0、耗时0.052秒，完整输出 `/private/tmp/pc68-r30-lifecycle-precheck.stdout.txt`。该次集成验证38项通过、退出0、0.138秒，输出 `/private/tmp/pc68-r30-lifecycle-integration-final-03.log`；同版判定检查47项通过、退出0、8.324秒，输出 `/private/tmp/pc68-r30-lifecycle-integration-runtime-final.log`。旧准备程序检查曾因独立预期缺少包及目标字段出现1项失败，历史原始输出 `/private/tmp/pc68-r30-lifecycle-prepare-precheck.stdout.txt` 保留；当前准备检查前后两轮均11项通过、退出0，耗时0.535/0.554秒，输出为 `/private/tmp/pc68-r30-final-prepare-before.log`、`/private/tmp/pc68-r30-final-prepare-after.log`，不将历史失败写成当前仍失败，也不称这两轮为刚发生的失败修复。以上不同轮次不与先前77项叠加成唯一证明数量。

后续有限解析边界检查26项中4项失败，修正后26项通过，最后28项通过，三份输出为 `/private/tmp/pc68-r30-parser-boundaries-before.log`、`/private/tmp/pc68-r30-parser-boundaries-after.log`、`/private/tmp/pc68-r30-parser-boundaries-final.log`。空引号未复现崩溃，只增加保守空路径处理；实际修正的4项反例证明：缺原始事件时不能仅凭已绑定快照判产品失败。有当前根轮次的有效事件时，独立已证失败仍优先保留。

组成入口检查通过真实仓库产品程序完成分配、固定捕获及首次计划，以合成原始事件构造完整前提，不替换业务解析和生命周期判定。5项包括合法整链通过、缺清理观察阻断、实际传递文件残留失败、其他请求文件被改写失败、请求边界损坏无效。它们属于判定程序验证，没有通过支持安装、没有教授正式运行。中间样例曾遗漏运行器保存清单的动作或出现路径前提不一致；全部尝试原文及计数仍保留于修正证据，不能把样例错误当产品失败。旧绑定样例另因动态加载模块身份错配导致1项失败，修正样例指向当前模块并保留原产品失败预期，输出 `/private/tmp/pc68-r30-bound-fixture-before.log`（22项中1项失败）、`/private/tmp/pc68-r30-bound-fixture-after.log`（基础28加集成22，共50项通过）。

顶层前一轮完整候选检查：生命周期基础及集成50项通过、3.057秒；运行判定47项通过、8.383秒；准备及步骤11项、环境12项通过，四个命令均退出0，共120项当轮检查。输出 `/private/tmp/pc68-r30-final-lifecycle-check.log`、`/private/tmp/pc68-r30-final-runtime-check.log` 和第4节两份最终日志。120是该轮检查总数，原样保留，不与旧轮次相加，也不是新增正式证明或验收结论。

最后核对另发现当前根最终消息歧义会提前返回无效，从而遮蔽严格关联根调用已证明的禁止参数违规。新增3项反例后50项中1项失败；修正后50项通过、退出0、9.442秒，完整输出 `/private/tmp/pc68-r30-final-ambiguity-before.log`、`/private/tmp/pc68-r30-final-ambiguity-after.log`。只在当前根最终消息歧义时核对严格原始事件的独立违规事实；没有确证违规仍无效，运行代次、顺序或轮次损坏仍无效，不从损坏事件构造产品失败。收集器源码未变，故沿用最终 `c5d8bd44` 对第04次的只读重解析结果，不再次请求。

根最终消息修正后，直接关联生命周期基础及集成50项再次通过、退出0、3.018秒，原文 `/private/tmp/pc68-r30-final-composed-after-ambiguity.log`；前轮50项日志保留。该轮候选检查为运行判定50项、生命周期50项、准备及步骤11项、环境12项，共123项，各命令退出0。123是该轮候选对应检查数量，完整保留于 `historical_candidate_validation_123`，不与前轮120或其他轮次累计为唯一证明；全部原文归档为 `tests/runtime/evidence/issue68-r30-review-fixes-validation.json`。正式D1按计划复用，R1仍未执行。

后续只读复核发现，重复根总览、成功重复分配、完整发现集合错误这三项已有独立事实，也可能被教授缺证或根最终消息缺失、歧义遮蔽。修正后先保留严格关联同一运行、当前根轮次和调用开始/完成配对的实际违规；旧轮次、损坏或缺失事件不能构造产品失败。新增反例首轮52项中9项失败，修正后52项通过、14.156秒，最后53项通过、16.938秒；原文分别为 `/private/tmp/pc68-r30-remaining-root-before.log`（13.724秒）、`/private/tmp/pc68-r30-remaining-root-after.log`、`/private/tmp/pc68-r30-remaining-root-final.log`，失败轮退出1，通过轮退出0。直接关联生命周期50项再检查通过、退出0、3.116秒，原文 `/private/tmp/pc68-r30-lifecycle-after-remaining-root.log`。最新候选共126项，即53项运行判定、50项生命周期、11项准备及步骤、12项环境检查；准备和环境沿用第4节已通过来源，不将历史123项或其他轮次累加。此次修正影响R1判定，D1复用依赖未变；收集器未变，不另发评估请求。所有原文分别归档于上述修正证据；两次支持安装超时及有限脚本观察缺口仍未解决，整体预检仍未完成，正式R1未执行。

第04次实际能力预检只发一次纯合成请求，状态 `SYNTHETIC_LIFECYCLE_READY`、退出0。真实根命令的创建、实际读取、删除顺序为22402/22403→22409/22410→22416/22417，运行代次为整数1；读取结果与独立合成预期相同，目标前后缺席，其他请求哨兵与服务未变。原始目录 `/private/tmp/pc68-r30-lifecycle-observation-04`，可访问投影为 `tests/runtime/evidence/issue68-r30-lifecycle-observation-04.json`。执行入口原字节摘要 `dce98777dd1cc05b2bf70644b268cced79df31a0f57f6b19a97560ac74cff288`；执行时收集器摘要 `718f84c3a7b51996b6adb06c07ee9d1a667b0af3084b3d084321d6e1eb276cef` 前后相同。中间收集器 `27d1cbc1a000d70b00edf4f585bf3887fc8bed72222b9dcba573bbd85b2f1e87` 及最终收集器 `c5d8bd442e8a14e6fd7f89c30aaf21ee14540f5597277308cdd8cfa95388449e` 分别只读重解析同一原始响应，均退出0，三项操作与结论未变，没有再次请求；投影保留原执行来源及两次重解析历史，不能把最终摘要冒充执行时源码。最终重解析原件为该目录的 `helper-reparse-c5d8bd44-refined.json`。

要复查第04次入口，`PC68_LIFECYCLE_ROOT` 取全新独占目录并先创建；其他变量与第4节同源。使用保存的入口原字节，不改写输入或观察程序：

```sh
mkdir "$PC68_LIFECYCLE_ROOT"
UV_CACHE_DIR=/private/tmp/pc68-r30-uv-cache uv run --no-project python .apm/skills/professor-contact/tests/runtime/preflight_issue68_lifecycle_observation_r30.py \
  "$PC68_RUNTIME_ROOT" "$PC68_LIFECYCLE_ROOT" "$PC68_EVAL_ROOT"
```

第04次只验证普通有限格式的真实观察能力，不证明完整教授生命周期或任意脚本副作用。未支持的任意脚本仍有观察缺口，审核者须确认该路线是否足以覆盖本例；不足时交测试设计审核者修订，不额外教代理改写业务来迎合解析。支持安装缺口依旧，总体仍 `PREFLIGHT_INCOMPLETE`，正式教授业务未执行。


最后限定复核另发现重复开始事件会覆盖原开始记录，导致损坏配对被当成独立违规证据。发现、分配和总览三个完整入口反例修前56项中3项失败，17.870秒、退出1；记录重复开始身份并排除后56项通过，17.368秒、退出0。原文 `/private/tmp/pc68-r30-duplicate-start-before.log`、`/private/tmp/pc68-r30-duplicate-start-after.log` 已归档。直接关联生命周期50项再检查通过，3.110秒、退出0，原文 `/private/tmp/pc68-r30-lifecycle-after-duplicate-start.log`。当前候选129项为56项运行判定、50项生命周期、11项准备步骤和12项环境检查；旧126项完整保留，不与其他轮次累计。仅影响R1判定，D1复用及收集器未变；未新增评估请求，安装和观察缺口仍保留，正式R1未执行。

## 6. 六终态、机器标签与总体分类


r25 的六种正式终态用于整例验收。逐教授保留各自真实业务结果的 `status`、`reason_code`、退出码和原始证据，核对根代理分别消费并原样报告；不额外要求每位教授生成六种测试终态。教授业务状态（例如缺核验早停）与判定程序的整例机器标签分别记录，退出码本身不能替代分类依据。

| r25 正式终态 | 机器标签或记录方式 | 适用条件 |
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

D1采用第二十五版明确指定的 `REUSE_PRIOR_PASS`。可访问脱敏证据为 `tests/runtime/evidence/issue68-d1-r29-history.json`，来源运行 `pc68-d1-r29-20261006`，原始包 `/private/tmp/pc68-d1-r29-20261006`。原产品 `35f2785b4d13783683860db910a36add2347bd29`、原测试 `e931ab22fbe492bdf0c4ecb74e906d2c23dfce23`，43唯一组件与7证明旧通过；原 `execution_kind=preflight` 原样保留，不能记成当前执行。第二十五版已核实产品差异仅帮助与注释、测试组件去重，P1—P7依赖未变，故复用旧结果，不本轮重跑D1。

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

运行器直接调用固定判定程序。对同一次已经保存的材料可用下列入口复核，禁止补写缺失事件或用新请求替代。`PC68_CASE_DIR` 指本次输出中的 `codex` 子目录，必须保存原始值；`PC68_RECHECK_JSON` 为新的判定输出文件，不覆盖原始结论。

```sh
UV_CACHE_DIR=/private/tmp/pc68-r30-uv-cache uv run --no-project python .apm/skills/professor-contact/tests/runtime/verify_issue68_stage5_routing_r19.py \
  --host codex --manifest "$PC68_CASE_DIR/fixture-manifest.json" \
  --events "$PC68_CASE_DIR/codex-response.json" \
  --shared-verdict "$PC68_CASE_DIR/codex-adapter.json" --output "$PC68_RECHECK_JSON"
jq '{verdict, formal_terminal, reason_code}' "$PC68_RECHECK_JSON"
```

D1依赖：P1本地来源/迁移；P2目标过滤/自身非法；P3整批/回滚；P4教授交易/校验/状态；P5总览派生/人工保护；P6发现读取；P7分配/归属/歧义/原值/包装。只有变化命中具体依赖才重开对应证明，不因提交编号变化全量重跑。

R1为 `EXECUTE_CURRENT`：观察、判定、输入和产品调用说明变化直接影响真实数据传递证明，旧失败/阻断运行不能重判补齐未发生的教授业务。依赖还包括支持安装、正式线程关系、结果回执、当前最终消息、独立总览输出、六项环境来源及文件隔离/清理。每次相关变化仅重新做受影响预检及直接关联检查，再由审核者冻结；正式执行者不得临场修测。外部故障只保留具体缺口，不改产品或降低证明要求。

正式输出须保存完整请求响应与原始事件、线程图、每次观察信封和实际参数/标准输出、根分配及消费回执、总览输出、输入与文件前后摘要、消费者及产品/共享/服务版本、服务前后来源与隔离、机器状态和六终态映射。原传递文件清理后证据副本仍可复查；清理仅本请求数据，不影响教授结果。保留所有历史尝试，不以二次运行覆盖失败。

当前待审范围是本记录、固定观察及判定修复、独立环境预检、生命周期收集、各轮真实判定及接线检查和可访问历史证据。两次支持安装均在窗口耗尽后超时，入口可执行性、安装摘要与帮助检查未完成；第04次已确认普通有限格式的真实生命周期观察能力，任意脚本副作用的未知范围仍须由审核者判断是否影响本例证明。本角色为部分完成，候选可固定提交供审核，不能以候选推送宣称测试实现全部就绪。当前缺口在关口前明确记录，不能推迟到正式验收补能力。第二关口完整批准不由本地测试工程师宣布；正式R1及第三关口尚未执行，本记录不授予合并许可。
