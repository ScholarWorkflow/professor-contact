# 第72号拉取请求完整测试方案第29版

方案编号：`issue-68-test-plan-r29-2026-10-07`。本版按用户要求将测试设计、完整执行步骤、必要预检、判定要求、历史尝试及复验交接整理成一份完整待审方案。执行者只需本文与本文指向的固定代码、原始证据及正式规范，不需要拼接旧计划或补充评论。

本版是唯一测试方案正文。旧版测试计划、旧执行步骤和独立预检补充正文全部删除，不归档副本；历史运行结果、原始证据及审核记录保留。本文收齐它们涉及的当前要求，执行者无需查阅旧计划。本版使用现有实现，不修改产品、测试代码、原始证据或既有通过条件，发布不代表独立批准。

修订原因：此前把新增预检留在补充记录，正式步骤仍指向旧设计，也未收齐目录预检与正式启动的对应要求。该交接缺口由本次完整方案纠正，不再要求执行者自行拼接。本次修订不证明此前教授业务执行有产品缺陷，也不重写安装失败和旧判定误判。

状态：文档整合完成；测试实现基线为 `d3d082667ecc19369c44c038a4147bcec8db9d4f`；第二关口仍待完整审核和冻结，第三关口未就绪；正式 `PC68-R1` 未执行。本方案作者的修订不算独立审批。

## 1. 权威来源与版本

| 项目 | 固定来源与版本 |
| --- | --- |
| 冻结验收 | `issue-68-gate1-r4-2026-10-05`，[第68号议题第四版](https://github.com/ScholarWorkflow/professor-contact/issues/68#issuecomment-5981562292)，决定人为 `RekiDunois` |
| 获批产品计划 | `issue-68-plan-r13-2026-10-06`，[第十三版](https://github.com/ScholarWorkflow/professor-contact/issues/68#issuecomment-6000673923)，[范围批准](https://github.com/ScholarWorkflow/professor-contact/pull/72#issuecomment-6008709709) |
| 当前完整测试方案 | 本文，`issue-68-test-plan-r29-2026-10-07`；仓库唯一正文为 `docs/issue68-test-plan.md`，拉取请求唯一入口为[完整方案](https://github.com/ScholarWorkflow/professor-contact/pull/72#issuecomment-6030951188) |
| 目标产品 | `b39a4252e3ce473f8cdeedd2e12b0cf86d6f597d` |
| 共享测试资产 | `c738fa2f8bcbb16cd99d741332d5f59b062b6357` |
| 本轮测试实现基线 | `d3d082667ecc19369c44c038a4147bcec8db9d4f`；本次发布只整合文档及更新其来源指针。审核者冻结时指定包含本文的完整提交，不另造自引用提交 |
| 历史安装续试基线 | 当时候选 `806066a`；对应安装恢复证据保留，不作为当前测试实现版本 |
| 证据约定 | `tests/runtime/issue68-runtime-evidence-contract-r19.json`，修订 `issue-68-runtime-evidence-r32-2026-10-07`；生命周期组合结构沿用原版本，新增传递位置绑定证据 |
| 规则来源 | 当前工作区的 `PROJECT_CONSENSUS.md` 和 `Test Engineer Rule.md`；本次整合已读取，以项目共识为先。原执行者当时未找到规则文件的历史事实保留，不作为本版未读取的声明 |

本文所有仓库内路径以 `.apm/skills/professor-contact/` 为前缀。产品不修改；不重开验收和产品计划。仅补测试观察、判定、预检与完整步骤。独立工作树为当前第72号拉取请求的测试工作树，执行前在仓库根运行 `pwd`，用返回值设置 `PC68_TEST_ROOT`；公共记录仅使用变量，真实值留本地原始证据。独占传递目录由测试人员按第4.1节选择、预检并记录绝对路径；运行器会核实其为空目录、加入实际请求声明与来源记录，并将同一目录纳入请求前后观察。

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
| AD68-1 | PC68-R1 | 根代理分别委派、等待并消费，之后最多一次总览并单独报告真实结果；当前代表场景应调用一次 |

每个组件由所属证明执行一次，不因多个要求引用而重复。确定性组件不能替代真实委派、实际读取或根结果消费；真实运行不能宣称证明未发生的渲染、提交及后续选择读取。


R1固定为缺核验前提。已经发生的分配、读取、首次计划、结果消费及总览须直接证明；不得要求或宣称尚未发生的后续选择读取、渲染、提交和校验。后续选择读取由D1/P7承担。

## 3. 完整输入、允许变量和实现文件

输入由固定 `tests/runtime/prepare_issue68_stage5_routing.py` 的 `EXPECTED_OWNERS` 和 `test_contact_state.write_issue59_stage5_fixture` 生成，不由执行者猜内容，不从根分配输出反推预期。两位教授为 `試験 教授`、`佐藤 花子`，编号分别为 `試験 教授::DIR00001::DIR00001_1`、`佐藤 花子::DIR00001::DIR00001_1`；每份独立选择保留 `first_choice=false`、`signature_name=試験 太郎`、`learning=比較手法の基礎知識の習得`，以及各自 `transport_sentinel=owner-0/owner-1`。完整原始选择另有 `email_id=unselected::D::I`、`transport_sentinel=noise` 的无关行。坏包由 `ISSUE59_MALFORMED_JSON` 写入 `教授研究/Z分野/无效样例`。两位教授证据为 `none`、核验为 `missing`；模板、原始结果、包及状态由固定准备程序写出。

准备程序只检查本例核验前提并生成独立预期，不生成根代理交接或分教授选择包，不替根代理分配。其 `fixture-manifest.json` 归档教授目录、包、编号、全部选择、首次计划业务数据、预期结果、坏包路径及执行前文件摘要；`canonical-choices.json` 保存完整原始输入，`root-prompt.txt` 保存业务提示词。位置绑定帮助分别保存 `codex/business-prompt.txt` 和 `codex/transfer-location-declaration.txt`，再将声明与业务提示合并交给固定请求构造器；绑定记录保存目录、声明与业务提示摘要及实际请求摘要。输入字节与初始状态以该固定程序及本次归档为唯一来源。

`PC68_PRODUCT_ROOT` 为干净产品检出目录，`PC68_SHARED_ROOT` 为固定共享资产的干净检出目录，`PC68_EVAL_ROOT` 为现有评估服务检出目录；先在各目录执行 `pwd` 取得绝对路径，保留到本次本地原始执行记录，再赋值，不在公共证据中泄露用户路径。`PC68_OUTPUT_ROOT` 为新建正式运行编号对应的空目录；`PC68_PREFLIGHT_ROOT` 和 `PC68_LOCATION_PREFLIGHT_ROOT` 是互不重叠、未创建的新合成预检输出目录，不使用已存在的第01或第02目录覆盖旧证据。

允许变量只有：产品检出绝对路径、共享检出绝对路径、评估服务检出绝对路径、全新且不相交的输出目录与运行编号、按第4.1节取得预检证据且初始为空的独占传递目录、缓存目录。这些由操作系统实际目录与服务 `direnv` 得到，执行前归档原值。产品与共享提交、输入内容、业务提示词、模型、执行器、观察程序、沙箱、入口和判定不得临场替换。位置声明与业务任务分开保存，但必须进入实际请求及其来源证据；产品自行决定实际文件名和布局。默认模型及推理设置引用当前项目共识，并由固定请求构造器落实，保存请求值及服务公开的实际生效配置；有效模型尚未公开时如实标注，不将请求值称为已观测的有效模型；端口由既有服务读取，不自行分配或启停服务。

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
| `tests/test_issue68_runtime_r19.py` | 独立已知输入的判定正例、产品失败和无效/阻断反例 |

## 4. 关口前最小预检与命令

先核对本文已列出的有效证据及源码、服务、配置、隔离条件和所选目录。未受影响的已完成检查直接复用，不重新发送请求。下面命令用于尚未完成或依赖已经变化的检查；只有该变化使旧证据不能复用时才执行，并记录变化及复验范围。第4.1节的目录对应检查每次正式启动前必做。

按本版测试计划，在第二关口完整通过前完成正式入口可执行、隔离、可归属观察和判定正反例验证，并完成独占传递位置的请求与观察绑定检查，以及第4.1节同一正式入口的实际创建、读取、清理预检。预检不运行完整教授业务，不委派教授，不产生正式验收结论；正式运行器的第二关口门继续有效。

执行前分别进入产品检出、共享检出、评估服务检出和测试工作树，运行 `pwd`，直接将返回路径设置为 `PC68_PRODUCT_ROOT`、`PC68_SHARED_ROOT`、`PC68_EVAL_ROOT`、`PC68_TEST_ROOT`，归档本地原值。进入测试工作树的 `tests/runtime` 后运行 `pwd` 设置 `PC68_RUNTIME_ROOT`，再回到仓库根。用未存在的新运行目录设置 `PC68_PREFLIGHT_ROOT`；目录不与任一源码、消费者、旧预检或正式输出相交。缓存变量 `PC68_UV_CACHE` 指向本轮独立临时缓存。正式输出 `PC68_OUTPUT_ROOT` 使用另一全新目录。`PC68_TRANSFER_ROOT` 是按第4.1节选定并取得实际预检证据的绝对空目录，不能是符号链接，不能和产品、共享、服务、消费者、输入或输出位置相交；真实路径只写本地原始证据，公共文件使用变量名。

```sh
UV_CACHE_DIR="$PC68_UV_CACHE" uv run --no-project python .apm/skills/professor-contact/tests/runtime/preflight_issue68_environment_r30.py \
  --producer-root "$PC68_PRODUCT_ROOT" \
  --fixture-root "$PC68_SHARED_ROOT" \
  --eval-direnv-root "$PC68_EVAL_ROOT" \
  --output-dir "$PC68_PREFLIGHT_ROOT"
```

该入口核对固定产品、共享资产及服务干净版本、隔离，然后按 `apm install https://github.com/ScholarWorkflow/professor-contact.git#b39a4252e3ce473f8cdeedd2e12b0cf86d6f597d --target codex --trust-transitive-mcp` 在隔离消费者支持安装，取得安装程序摘要和帮助退出码。安装保护窗口为600秒；失败或超时保留终态，不默默重跑。用户授权续试，或新的恢复事实或有区分作用的最小诊断成立时，按原支持路径新建消费者目录继续原来未完成的检查，不改产品、依赖引用或服务。成功安装后只发一次纯合成普通命令请求，复制一次真实解析对象，并由同一对象启动回显子进程；不读取教授包、不分配、不委派、不启停服务。

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
UV_CACHE_DIR="$PC68_UV_CACHE" uv run --no-project python .apm/skills/professor-contact/tests/runtime/preflight_issue68_lifecycle_combination_r31.py "$PC68_COMBINATION_ROOT"
jq '{state, formal_case_started, cases, uncompleted}' "$PC68_COMBINATION_ROOT/summary.json"
```

传递位置请求与观察的本地合成预检使用新的空输出目录 `PC68_LOCATION_PREFLIGHT_ROOT`，调用实际请求构造器与生命周期观察器；只运行本地文件操作，不发送评估请求。每个场景保存实际请求、清单、请求前快照、合成实际读取、响应、请求后快照、生命周期证据及机器判定；汇总记录保存场景预期、终态、源码摘要和运行边界，命令与退出码另记入配套证据。成功场景须证明选定位置的请求前后完整快照相同且为空。七个场景均符合固定预期且命令退出0时，才记 `TRANSFER_LOCATION_PREFLIGHT_READY`。

```sh
UV_CACHE_DIR="$PC68_UV_CACHE" uv run --no-project python .apm/skills/professor-contact/tests/runtime/preflight_issue68_transfer_location_r32.py "$PC68_LOCATION_PREFLIGHT_ROOT"
jq '{state, formal_PC68_R1_started, eval_service_called, cases, source_sha256}' "$PC68_LOCATION_PREFLIGHT_ROOT/summary.json"
```

每个场景保存 `request.json`、`before.json`、`actual-use.json`、`response.json`、`manifest.json`、`lifecycle-evidence.json`、`after.json`、`result.json`，总记录为 `summary.json`。本轮七种场景为：成功形成、读取并清理；传递文件残留；既有保护数据变化；错请求；漏扫；缺少实际使用；传递位置超出观察范围。成功链的文件形成、读取、清理及完整目录记录来自本地实际文件操作；线程、轮次、运行代次和事件信封是合成材料。该预检证明新增位置接线与合成判定可区分七种场景，不证明正式评估线程归属、根代理实际转交或教授业务结果。第03、04次原始记录仅保留其真实能力来源。

固定程序验证入口如下；每个新检查的完整输出使用独有文件保留，记录该轮版本、命令、退出码及耗时，不把多轮项数累加。样例预期由本版设计和独立已知输入确定，不由当前判定器反推。

```sh
UV_CACHE_DIR="$PC68_UV_CACHE" uv run --no-project python -m unittest discover -s .apm/skills/professor-contact/tests -p test_issue68_runtime_r19.py
UV_CACHE_DIR="$PC68_UV_CACHE" uv run --no-project python -m unittest discover -s .apm/skills/professor-contact/tests -p 'test_issue68_lifecycle*.py'
UV_CACHE_DIR="$PC68_UV_CACHE" uv run --no-project python -m unittest discover -s .apm/skills/professor-contact/tests -p test_issue68_runtime_recipe.py
UV_CACHE_DIR="$PC68_UV_CACHE" uv run --no-project python -m unittest discover -s .apm/skills/professor-contact/tests/runtime -p test_preflight_issue68_environment_r30.py
UV_CACHE_DIR="$PC68_UV_CACHE" uv run --no-project python -m unittest discover -s .apm/skills/professor-contact/tests -p test_issue68_transfer_location.py
UV_CACHE_DIR="$PC68_UV_CACHE" uv run --no-project python -m unittest discover -s .apm/skills/professor-contact/tests -p test_issue68_transfer_location_eval_r33.py
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

第30版检查原文及修正历史见 `tests/runtime/evidence/issue68-r30-precheck-validation.json`、`tests/runtime/evidence/issue68-r30-review-fixes-validation.json`；保留每轮失败及通过的原始计数、恢复日志的可见范围和源码摘要，不把历史129项或更早轮次写成当前检查。原丢失日志的恢复仅覆盖原工具可见部分，不能称完整原始日志，不重跑冒充旧轮次。第26版对损坏样例审核依据的撤回不改写这些历史尝试。

前四次安装续试由用户在候选 `806066a` 推送后授权，均沿用固定产品提交、原支持安装命令及600秒预算；证书和传输设置仅作用于对应进程，证书验证保持开启。四次失败、恢复诊断、原始日志和独立审核结论见 `tests/runtime/evidence/issue68-r31-install-retry-review-20261007.md`，不覆盖先前超时。随后用户要求只重试安装。第05次在独立临时消费者中38.838秒退出0；锁文件固定到产品提交 `b39a4252e3ce473f8cdeedd2e12b0cf86d6f597d`，已安装 `contact_state.py` 摘要与产品源相同。独立限定复核确认上述数据一致，并确认修正后的锁文件摘要正确，见 `tests/runtime/evidence/issue68-r31-install-only-retry-review-20261007.md`。完整命令和输出摘要见新增安装证据。该轮没有运行入口帮助、合成评估或正式业务，因此只确认本次支持安装成功，不能据此宣布完整预检完成。

历史执行记录：随后按用户要求执行完整环境预检：第02次在依赖解析阶段达到600秒上限；一次只读 `git ls-remote` 成功后，第03次在新消费者中约46秒完成，安装10项依赖并配置1个模型上下文协议服务。固定产品提交与安装入口摘要一致，`--help` 退出0；唯一评估请求只解析并原样转交一份合成对象，输出退出0且通过同一调用关联检查。证据和原始摘要见 `tests/runtime/evidence/issue68-r31-environment-preflight-retry-20261007.json`。此次仅将环境预检更新为 `PRECHECK_READY`；当时正式合法临时传递位置覆盖仍未证明；本版当前目录证明状态见第4.1节，历史结论不改写。

历史第30版第03次实际请求模型为 `gpt-6-luna`、推理强度 `low`；当时服务工具为 `codex-cli 0.159.0-alpha.12.1`，本地准备工具 `codex-cli 0.160.1`。服务内部最终模型未公开，不宣称取得。第01、02次服务提交 `3fdfa9387140cfc2e2aa3af415f85015f79706d2` 仅为当次来源，不能充当本次实值。第31版完整预检第03次的实际配置、工具及服务前后摘要见新增证据。当前环境预检为 `PRECHECK_READY`，第二关口仍为 `INCOMPLETE`；后续证据须先解析核对再更新本记录。

### 4.1 同一正式入口目录预检与正式准入对应

本节直接纳入第33版实际步骤及证据，取代第32版仅凭宿主合成动作证明目录可执行的安排。合成检查仍证明观察与判定；正式入口实际操作证明所选目录可用，两者不能互相替代。

正式目录操作仅创建、读取核对、删除一个无业务含义的标记；使用与R1相同的请求构造器、评估入口、请求模型、推理设置、沙箱及隔离条件。不得由宿主程序代替这三项操作，不处理教授业务、不真实委派、不启停现有服务。

**已有证据及处理**：第33版第一次安装失败，原状态 `CASE_NOT_STARTED`，没有发出请求；连通性恢复后使用新消费者，第二次只发出一个请求。旧判定器误把普通根代理 `agentMessage` 当作委派，将结果记录为 `INVALID_TEST_EXECUTION`。修正判定器后对相同完整原始证据重新判读为 `PASS`，未覆盖原结果，未发送新请求。本次原件核对确认唯一命令在事件23435开始、23436结束、退出0，读取相符、删除后缺席、同根前后快照完整且为空，消费者和服务不变。这不是正式R1通过。

| 对象 | 固定来源 |
| --- | --- |
| 第33版实现及脱敏证据 | 测试提交 `d3d082667ecc19369c44c038a4147bcec8db9d4f`；`tests/runtime/evidence/issue68-r33-transfer-location-eval-preflight.json` |
| 实际请求摘要 | `88283d916a7af0b61bb20e4eb7459ab3ad989e262e005834514000445a5665cc` |
| 实际响应摘要 | `92fff452afbeddfaea2c530a8a664730aedec3e9a580325ab6c8233286ceb403` |
| 原判定文件摘要 | `55119453767f338da60f3d307dc6c0fbc20b4cfe948ab7ed60eb458f6c533ad2`，原无效状态保留 |
| 修正后预检程序摘要 | `abab912f50a4d35df18369743c176bbb2761b4a2da19f445bd648070561e203d` |
| 原始材料定位 | 第二次运行 `50f0ee67-0ced-435a-bffb-2ba9c0ed475a` 的独占证据目录；公开别名 `$PC68_R33_RUN02_RAW`，实际位置由本地证据保管者提供，不在公开方案披露 |

第33版定向验证共31项，当前实现提交及当时干净推送副本均退出0；来源、原始日志摘要及完整尝试保存在上述机器可读证据。其范围为目录隔离、实际请求、前后观察、事件分类及重判，不代表教授业务或正式委派已经验证。本次文档整合不重跑这些检查。

**正式准入检查**：发送正式R1前，执行者记录实际 `PC68_TRANSFER_ROOT`，并与有效目录预检的请求、命令输出和前后快照中的根路径逐项对应；同时核对产品、共享资产、服务、请求构造器、沙箱和隔离条件。只复用真实证明同一所选目录且相关条件仍有效的证据。目录仍须为空、独占、不重叠，不得把预检消费者用作正式消费者。目录、权限或相关配置改变时，停止正式启动，交本地测试工程师补充受影响的最小预检及审核；不能以另一目录的成功记录放行。未变化的已完成检查不重复执行。若旧证据缺少可定位原件或无法完成对应核对，保持未完成状态，不推定通过。

需要补充目录预检时，以下是已存在的固定入口及准备步骤。仅在证据确实不适用时由本地测试工程师执行；本次文档整合不执行这些命令。目录名是该测试程序的既有输入限制，不是新增产品要求。

运行位置为包含本记录和预检程序的测试仓库根目录；先在三个已准备的本地检出目录中解析来源根路径，路径只保存在当前 shell。产品检出须固定在 `b39a4252e3ce473f8cdeedd2e12b0cf86d6f597d`，共享夹具检出须固定在 `c738fa2f8bcbb16cd99d741332d5f59b062b6357`，评估服务检出须固定在 `3fdfa9387140cfc2e2aa3af415f85015f79706d2` 并使用其 `direnv` 环境；三者均须干净。`PC68_PRODUCT_CHECKOUT`、`PC68_SHARED_CHECKOUT` 和 `PC68_EVAL_CHECKOUT` 是本机已准备好的检出目录输入，不写入公开证据。运行下列准备命令时，当前目录必须是测试仓库根目录：

```sh
PC68_TEST_ROOT="$(pwd -P)"
: "${PC68_PRODUCT_CHECKOUT:?设置为已固定版本的产品检出目录}"
: "${PC68_SHARED_CHECKOUT:?设置为已固定版本的共享夹具检出目录}"
: "${PC68_EVAL_CHECKOUT:?设置为已固定版本的评估服务检出目录}"
PC68_PRODUCT_ROOT="$(cd "$PC68_PRODUCT_CHECKOUT" && pwd -P)"
PC68_SHARED_ROOT="$(cd "$PC68_SHARED_CHECKOUT" && pwd -P)"
PC68_EVAL_ROOT="$(cd "$PC68_EVAL_CHECKOUT" && pwd -P)"
test "$(git -C "$PC68_PRODUCT_ROOT" rev-parse HEAD)" = "b39a4252e3ce473f8cdeedd2e12b0cf86d6f597d"
test -z "$(git -C "$PC68_PRODUCT_ROOT" status --porcelain)"
test "$(git -C "$PC68_SHARED_ROOT" rev-parse HEAD)" = "c738fa2f8bcbb16cd99d741332d5f59b062b6357"
test -z "$(git -C "$PC68_SHARED_ROOT" status --porcelain)"
test "$(direnv exec "$PC68_EVAL_ROOT" git -C "$PC68_EVAL_ROOT" rev-parse HEAD)" = "3fdfa9387140cfc2e2aa3af415f85015f79706d2"
test -z "$(direnv exec "$PC68_EVAL_ROOT" git -C "$PC68_EVAL_ROOT" status --porcelain)"

umask 077
PC68_R33_RUN_ROOT="$(mktemp -d /private/tmp/pc68-r33-transfer-eval-preflight-XXXXXX)"
mkdir "$PC68_R33_RUN_ROOT/transfer"
PC68_TRANSFER_ROOT="$PC68_R33_RUN_ROOT/transfer"
test -z "$(ls -A "$PC68_TRANSFER_ROOT")"
test "$(ls -A "$PC68_R33_RUN_ROOT")" = "transfer"
test ! -e "$PC68_R33_RUN_ROOT/evidence"
uv run --no-project python "$PC68_TEST_ROOT/.apm/skills/professor-contact/tests/runtime/preflight_issue68_transfer_location_eval_r33.py" \
  --producer-root "$PC68_PRODUCT_ROOT" \
  --fixture-root "$PC68_SHARED_ROOT" \
  --eval-direnv-root "$PC68_EVAL_ROOT" \
  --transfer-root "$PC68_TRANSFER_ROOT" \
  --output-dir "$PC68_R33_RUN_ROOT/evidence"
```

五个程序参数依次来自已核对版本的产品检出、共享夹具检出、评估服务 `direnv` 检出、新建运行目录中的空 `transfer/`，以及同一运行目录下尚不存在的 `evidence/`。输出目录由程序创建。读取结果时，不以进程退出码代替状态判定；退出码非零时仍检查已写出的结果文件：

```sh
jq '{state,reason,request_attempted,request_body_sha256,response_body_sha256,observation,integrity}' \
  "$PC68_R33_RUN_ROOT/evidence/preflight-result.json"
```


预检请求发送后不作同条件重试；请求未发送且前提经独立诊断恢复时，仅继续未完成的前置检查，使用新消费者并保留所有旧尝试。目录操作成功只确认必要执行能力。状态按本方案第6节分类；普通根代理消息不构成委派，真实委派或子线程事件须按固定判定程序处理。

已有离线重判只改变事件解释，原始材料完整，可以复用；不再要求重新发请求。正式R1尚无当前执行材料，不能用这次重判补齐正式业务事实。

## 5. 正式 PC68-R1 固定步骤

第二关口审核者指定包含本文的唯一完整固定提交，并明确完整通过与正式许可后，才允许正式入口调用。现有契约保持 `second_gate_status=INCOMPLETE`、`formal_run_allowed=false`；本地测试工程师不自行改为通过。正式消费者与输出另建，不能复用合成预检消费者。

工作目录为获批测试提交所在的仓库根目录，使用固定命令；下列大写变量按第3节实际目录取值，先保存到本次执行记录：

```sh
UV_CACHE_DIR="$PC68_UV_CACHE" uv run --no-project python .apm/skills/professor-contact/tests/runtime/run_issue68_stage5_routing_r19_codex.py \
  --producer-root "$PC68_PRODUCT_ROOT" --producer-sha b39a4252e3ce473f8cdeedd2e12b0cf86d6f597d \
  --fixture-root "$PC68_SHARED_ROOT" --fixture-sha c738fa2f8bcbb16cd99d741332d5f59b062b6357 \
  --eval-direnv-root "$PC68_EVAL_ROOT" --output-dir "$PC68_OUTPUT_ROOT" \
  --transfer-location-root "$PC68_TRANSFER_ROOT"
```

启动边界是完成第二关口冻结及第4.1节目录预检对应检查，并由正式运行器完成版本、干净消费者安装、输入与输出隔离、六项环境证据及观察检查后，写入本次启动记录并发送唯一正式请求。边界前失败是 `CASE_NOT_STARTED`。正式请求一旦发送，不换模型、不重试、不另发评估请求代替委派。

六项实际事实来源：`model`取本次请求；`executor`取实际编码执行分支的函数/模块和源文件摘要；`entrypoint`取已安装 `contact_state.py` 路径/摘要；`isolation`取服务与存储前后快照；`shared_assets`取固定产品/共享干净提交及锁文件摘要；`service_version`取本次只读服务干净提交并前后比较。监听进程只作服务来源，不能冒充执行器。预检记录验证来源可用，正式请求仍重新保存本次实值到 `runtime-environment-evidence.json`、`input-evidence-preflight.json`、`provenance.json`，不拿旧预检替代本次记录。


步骤按表中顺序执行。任何前置门未通过即停止，不得跳到下一步。PC68-R1 只允许一次正式服务请求，不重试，不更换模型、执行器、服务或入口来寻找成功。

| 步骤 | 操作和实际输入来源 | 必须保存的直接证据及核对条件 | 停止条件 |
| --- | --- | --- | --- |
| 0. 冻结与准入 | 使用唯一完整测试实现版本、获批产品目标和本版计划及本文完整记录；完成第二关口审核及第4节全部必要预检，按第4.1节核对正式选定目录与有效预检来源 | 审核指定版本、产品与测试完整 SHA、入口及判定程序版本；确认正式入口类别未改，产品代码未为测试修改 | 第二关口未完成时先记 `CASE_NOT_STARTED`，仅禁止正式业务请求；候选 SHA 未固定、预检不通过或任一必填事实未知时也不启动 PC68-R1。当前状态即为此门未通过 |
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
| 11. 后置检查与清理 | 请求结束后检查本地状态、传递文件和服务隔离；只清理本请求临时数据 | 本地状态前后快照、相关文件内容/校验值、同请求前记录、实际使用、后记录与保护数据组合；证明没有跨教授写入、总览反向修改教授结果，观察副本在原文件清理后仍可复查；请求后服务 provenance 与请求前一致 | 服务进程或存储隔离变化、证据被污染或不能归属为无效执行；真实跨教授写入为产品失败。清理不能删除其他请求数据，清理错误不得改写教授结果 |

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

运行器直接调用固定判定程序。对同一次已经保存的材料可用下列入口复核，禁止补写缺失事件或用新请求替代。`PC68_CASE_DIR` 指本次输出中的 `codex` 子目录，必须保存原始值；`PC68_RECHECK_JSON` 为新的判定输出文件，不覆盖原始结论。

```sh
UV_CACHE_DIR="$PC68_UV_CACHE" uv run --no-project python .apm/skills/professor-contact/tests/runtime/verify_issue68_stage5_routing_r19.py \
  --host codex --manifest "$PC68_CASE_DIR/fixture-manifest.json" \
  --events "$PC68_CASE_DIR/codex-response.json" \
  --shared-verdict "$PC68_CASE_DIR/codex-adapter.json" --output "$PC68_RECHECK_JSON"
jq '{verdict, formal_terminal, reason_code}' "$PC68_RECHECK_JSON"
```

D1依赖：P1本地来源/迁移；P2目标过滤/自身非法；P3整批/回滚；P4教授交易/校验/状态；P5总览派生/人工保护；P6发现读取；P7分配/归属/歧义/原值/包装。只有变化命中具体依赖才重开对应证明，不因提交编号变化全量重跑。

R1为 `EXECUTE_CURRENT`：观察、判定、输入和产品调用说明变化直接影响真实数据传递证明，旧失败/阻断运行不能重判补齐未发生的教授业务。依赖还包括支持安装、正式线程关系、结果回执、当前最终消息、独立总览输出、六项环境来源及文件隔离/清理。每次相关变化仅重新做受影响预检及直接关联检查，再由审核者冻结；正式执行者不得临场修测。外部故障只保留具体缺口，不改产品或降低证明要求。

正式输出须保存完整请求响应与原始事件、线程图、每次观察信封和实际参数/标准输出、根分配及消费回执、总览输出、输入与文件前后摘要、消费者及产品/共享/服务版本、服务前后来源与隔离、机器状态和六终态映射。原传递文件清理后证据副本仍可复查；清理仅本请求数据，不影响教授结果。保留所有历史尝试，不以二次运行覆盖失败。

当前待审变化为完整方案整合、目录预检与正式目录对应要求、旧计划删除及当前来源指针更新。生命周期、原输入观察、正式委派、结果消费、独立总览和D1的未受影响证明继续复用。本次属于第二关口首次完整通过前的交接修正，不重开第一关口或第十三版执行计划，不产生产品修复任务。

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

当前合成位置预检与第31版环境证据继续按其原版本复用；第33版所选目录的正式入口最小操作证据已完成并经原始材料核对，见第4.1节。本文为完整待审候选，第二关口尚未完整通过，正式 `PC68-R1` 未执行。正式许可仍关闭，不能以整合文档或预检通过代替正式验收。

## 10. 当前交接与完成条件

本次变化仅收齐目录预检与正式交接并删除旧计划，未改变验收第四版、实现计划第十三版、两个正式用例及其证明责任。D1继续复用历史通过；已有环境与合成判定检查按固定源码和依赖复用；第33版目录操作使用完整原始证据重判来源。正式R1仍采用 `EXECUTE_CURRENT`，冻结后建立新的正式消费者。

本地测试工程师核对本文归并的既有命令、代码、来源和准入条件，确认测试实现支持本文的目录预检对应要求，提交第二关口完整材料。证据约定的当前方案指针随本文发布同步更新；历史证据版本和正式许可不变。未经独立完整批准，不把许可改为开放。若代码与本文发生影响执行或判定的冲突，先记录并修正受影响实现，不由正式执行者临场补救。

审核者按测试规则第3.3节检查本文与固定测试实现：唯一完整来源、需求对应、最小充分用例、命令和输入、隔离、直接证据、有效成功/有效失败/无法判断三类判定、预检版本及目录对应、终态唯一性和复验来源。完成后才给出独立第二关口结论和冻结版本；本方案不自行授予通过。

第二关口完整通过后，本地执行代理按第5节全部步骤执行正式R1，保留全部尝试和证据，不改提示词、参数、判定或源码。审核者随后审核第三关口结果。没有独立冻结或当前R1有效结果时，合并仍未就绪。
