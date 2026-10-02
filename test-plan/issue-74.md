# 第 74 号议题测试方案第 1 版

## 状态与唯一来源

- 修订号：`issue74-test-r1`；状态：待第二关口审核，未执行正式验收，不声明通过。
- 本文件及同一提交的 `.apm/skills/professor-contact/tests/test_issue74_fixture_support.py` 构成完整方案。后续修改在本文件合入，更新修订号；不维护评论补丁。
- 取代范围：第 74 号议题正文的“测试安排草案”。不取代需求、已批准执行计划或任何已有测试通过记录。
- 正式需求：[第 74 号议题需求第 1 版](https://github.com/ScholarWorkflow/professor-contact/issues/74)，读取更新时间 `2026-10-02T16:02:24Z`；决定人为议题记载的项目负责人。
- 执行计划：[第三版](https://github.com/ScholarWorkflow/professor-contact/blob/a328e788a21af8fc7d3ebf052c399054d242b786/plan/issue-74.md)。计划审核来源为项目工作目录《第75号拉取请求-第三版执行计划复审-2026-10-03.md》，批准只覆盖实施。
- 兼容基准：`768b49ef4514e36edec6b57ed3821a99af9e9c00`。测试读取该固定提交的两个旧入口作为合法成功结果的独立参照，不用当前共用工具生成预期值。
- 待测产品：后续完成迁移的准确提交，由执行前的 `git rev-parse HEAD` 记录。目前请求只含执行计划，没有共用模块；本方案不宣称旧实现已满足新安全约定。
- 方案和判定版本：审核者须绑定包含本文件和测试文件的准确提交；判定入口为该获审版本的 `tests/gate2_evidence.py`。执行前核对文件内容与获审版本一致。产品、方案、判定提交可以不同，分别记录。
- 规则来源：项目正式 `PROJECT_CONSENSUS.md`、`Test Engineer Rule.md`，以前者为准。规则文件在项目工作目录，不把草稿复制为本仓库规范。

## 范围和证明归属

所有路径在下表中相对于 `.apm/skills/professor-contact/`。新增测试类为 `test_issue74_fixture_support.Issue74FixtureTests`。每个方法是一个用例；方法内子用例只区分会改变行为的条件。测试作者负责设计，执行者保存证据，审核者判断有效性；作者不替独立审核者宣布关口通过。

| 要求／证明 | 唯一负责者和用例 | 直接观察事项 |
| --- | --- | --- |
| R1：测试归属、虚构数据；R2：两个入口共用三类操作及成功兼容 | `test_compatibility_bytes_manifest_hashes_and_returns`；归属及禁止业务改动另由 S74 源码检查负责 | 共用模块位于 `tests/runtime/fixture_support.py`；两个真实入口各自产生来自共用模块调用栈的目录创建、文件写入、摘要计算事件；固定旧版本与当前版本在同一路径下的返回对象、全部文件字节一致；摘要由标准库独立重算；原包装返回保留；禁止输出缺席 |
| R2：命令和按文件加载两种方式 | `test_cli_from_unrelated_directory_without_pythonpath` | 按文件加载用于所有新增用例；两个旧脚本从无关目录直接启动，不设置 `PYTHONPATH`；成功退出及结构化字段保持原约定；失败退出为 1、状态为 `error`，既有文件字节不变 |
| R3：预先拒绝危险路径与清单冲突 | `test_preexisting_conflicts_fail_before_any_sample_write` | 文件根、非空根、已有文件／目录清单、清单与样例重合、生产者内根／输出：原字节保留，未创建其他样例；保持旧 `FixtureBuildError` 通道 |
| R3：第 53 号双根独立 | `test_equal_and_nested_issue53_roots_are_rejected_without_changes` | 根相等、两种祖先关系均拒绝；根和清单未创建 |
| R3：已有空目录不删除重建 | `test_existing_empty_root_identity_is_preserved` | 已有目录设备编号与目录编号保持；不得调用删除该目录的操作 |
| R3：不同运行独立 | `test_different_runs_do_not_share_writable_outputs` | 两次独立分配后，修改右侧文件，左侧全部字节不变 |
| R3：同一解析路径占用、正常释放 | `test_overlapping_call_cannot_recreate_first_empty_root` | 第一调用取得空根、首次写入前，第二调用经符号链接指向同一真实根；第二调用拒绝，原目录编号保留、第二输出缺席；第一调用成功；父目录无残留占用 |
| R3：清单检查后的创建冲突 | `test_manifest_creation_race_preserves_competing_bytes_and_partial_samples` | 清单实际打开前插入其他调用字节；写入失败且不覆盖竞争者；本次部分样例仍存在，占用释放 |
| R3：第 53 号第二根失败回滚 | `test_second_root_failure_rolls_back_only_new_owned_first_root` | 第二根创建失败：本次新建第一根删除；调用前已有空根保持原目录编号；被替换的第一根及其新内容保留；无清单或遗留占用 |
| R3：写入失败保留部分样例 | `test_sample_write_failure_preserves_partial_samples` | 资料写入故障发生后，已写 `info.json` 保留、清单缺席、占用释放 |
| R3：异常占用拒绝接管 | `test_abrupt_exit_leaves_occupation_and_next_call_cannot_take_over` | 子进程在首次写入前以 91 退出，跳过正常释放；占用保留；下一调用拒绝且不改变文件或路径集合 |
| R4：产品失败、准备无效、空执行分类 | P74：既有 `test_gate2_evidence.Gate2EvidenceTests` 的判定通道验证 | 有效成功为 `PASS`；有效产品断言或调用失败为 `FAIL`；准备无效、空执行、缺少证明等保持对应非通过终态；产品失败不会被后续清理错误掩盖 |
| R1 非目标、R4 文档职责与使用方法 | S74：下文固定源码与文档检查 | 差异仅在计划允许范围；使用说明区分准备／执行／判定／业务样例，给出新增样例、独立目录、异常占用清理及实际运行步骤 |
| 两入口现有业务验收兼容 | G74：一次完整回归中的既有 `test_issue53_stage4_runtime_assets`、`test_issue55_stage3_runtime_assets` | 沿用这两个版本化测试的原断言，禁止为本次迁移降低判定条件 |

兼容字节用例分别覆盖根外清单和合法根内新清单，防止一律拒绝根内输出。只比较固定同一路径的字节；路径文本属于生成内容，不能把不同路径产生的字节差异当作回归。独立摘要比较不调用被测 `sha256` 作为唯一参照。

同样共享操作、相同判定的其他目录名称和虚构教授名称为等价输入，由上述用例代表；业务状态字段由固定基准和第 53、55 号旧测试负责。生产者真实检出不作为危险写入目标：目录拒绝用例只把调用方 `_producer_root` 的输入替换为隔离空间内的虚构生产者；不修改共用模块或生成业务对象。不新增真实代理、浏览器、文献服务或安装测试：这些调用链未变化，且当前要求由生产者本地确定性检查证明。

## 输入、隔离和故障注入

固定解释器为通过 `uv run --no-project --python 3.12` 取得的 CPython 3.12；无额外包。记录实际补丁版本，不能只写预期版本。测试子进程使用同一 `sys.executable`。基准源码在内存加载，真实入口在当前生产者按文件加载；本轮不是安装证明，不创建或修补消费者。

每个方法在 `TMPDIR` 下创建独占 `TemporaryDirectory`，拒绝位于生产者内的临时空间。所有路径、符号链接、竞争者内容、替换目录和异常进程均属于该隔离空间。测试结束整体清理自有空间，不连接真实用户目录或状态；故障前后的必要字节和路径关系由断言纳入结构化事件。这里整体清理测试自有空间不等于授权被测准备工具清理遗留占用。

故障注入固定在 `Path.open` 和 `Path.mkdir` 的文件操作边界：只控制竞争顺序或一次操作故障，不改变产品返回值、不重写业务输入、不代替调用方执行传递。调用栈观察使用 `sys.setprofile`，不以内部函数名称作为验收条件。程序会断言注入点被真实到达；未到达时先检查下面的执行前假设，不得直接将观察程序的失效认定为产品失败。

异常退出子进程最多运行 30 秒，超时保存原始诊断并以 `TestPreparationError` 标为执行无效；不重试。实际故障进程应由 `subprocess.run` 的超时处理结束，本用例不启动孙进程。

## P74：第二关口的执行前检查

本次作者仅阅读代码和官方约定，未运行以下检查，不能宣布第二关口完整通过。第二关口审核时完成这些适用检查并将结果绑定准确提交；不得用产品完整验收代替检查。

- 可执行：旧入口、`gate2_evidence.py` 与原测试命令已有固定源码；新共用模块尚待实施。检查实际 CPython 3.12 中 `Path.open`、`Path.mkdir` 与 `hashlib.sha256` 能提供当前观察事件；源码改变操作方式时，先修订观察程序，不新增产品要求。
- 隔离：确认临时目录在生产者外、没有共享可写状态；异常进程只访问自有目录；生产者路径负例使用虚构目录。
- 可观察：确认迁移后的两个入口分别使用共用模块完成三种操作，清单确实经过声明的打开边界，第二根确实经过声明的创建边界。只需对应源码及最小非验收观察，不重复完整业务准备。
- 可区分：执行下列现有判定通道样例；样例预期由 R4 与测试审核规则决定，不由判定程序自述决定。有效失败及无效样例是被验证程序的输入，外层样例验证成功时其检查结果为 `PASS`。

以下命令从仓库根运行。先使用下节的目录分配与版本记录步骤，再执行：

```sh
uv run --no-project --python 3.12 .apm/skills/professor-contact/tests/gate2_evidence.py --start .apm/skills/professor-contact/tests --pattern test_gate2_evidence.py --require-prefix test_gate2_evidence.Gate2EvidenceTests. --out "$RUN_DIR/preflight.json" > "$RUN_DIR/preflight.stdout" 2> "$RUN_DIR/preflight.stderr"
jq '{schema_version,python,selection,tests_run,started,completed,events,load_errors,interruption,verdict}' "$RUN_DIR/preflight.json"
```

需完整读取全部样例及结果；记录三种通道、失败后清理／中断仍保留失败、空执行与缺少证明不能通过的结果。检查失败时暂停依赖该判定程序的验收，分析是判定程序、检查样例或环境问题。不得将这次非产品执行写成产品通过。

官方依据：[CPython 3.12 调用栈观察](https://docs.python.org/3.12/library/sys.html#sys.setprofile)、[文件操作](https://docs.python.org/3.12/library/pathlib.html#pathlib.Path.open)、[结构化测试结果](https://docs.python.org/3.12/library/unittest.html#unittest.TestResult)。这些依据说明接口，不证明本次操作钩子已到达；本方案不声称已完成最小观察。

## S74：固定源码与文档检查

执行者从准确产品提交保存基准到产品的完整差异、共用模块、两个准备入口和实际使用说明全文。使用说明文件位置是唯一可代入变量 `DOC_PATH`：实施提交中 R4 使用说明的仓库相对路径，由实施记录明确指定；审核记录固定该值后，执行者不得换成其他文件。

```sh
git diff 768b49ef4514e36edec6b57ed3821a99af9e9c00 HEAD > "$RUN_DIR/product.diff"
git show HEAD:.apm/skills/professor-contact/tests/runtime/fixture_support.py > "$RUN_DIR/shared-source.py"
git show HEAD:.apm/skills/professor-contact/tests/runtime/prepare_issue53_stage4_fixture.py > "$RUN_DIR/entry53.py"
git show HEAD:.apm/skills/professor-contact/tests/runtime/prepare_issue55_stage3_fixture.py > "$RUN_DIR/entry55.py"
git show "HEAD:$DOC_PATH" > "$RUN_DIR/usage.md"
```

任何读取失败则此证明未完成，不把空输出当通过。审核者完整阅读这些版本化静态产物并在执行记录逐项记录“满足／不满足”、准确文件与位置及依据：

1. 共用模块只负责目录、文件和摘要；虚构数据仍由两调用方拥有；没有启动浏览器、外部服务、代理或读取用户资料的路径。
2. 没有迁移范围外准备入口，没有修改业务程序、状态接口、代理配置或其他议题的验收断言。判定程序保持产品失败优先、空执行非通过；如确有变化，先分析影响并修订方案，不静默复用。
3. 使用说明区分四项职责，包含旧入口参数、如何新增议题专属样例、如何执行并按结构化结果判断、独立目录分配、异常占用不得自动接管及隔离空间整体清理责任。

静态产物是证据正文，审核记录是其语义判断；不以文件存在、关键词命中或作者“已完成”代替上述检查。S74 是实现范围和文档证明，不重复运行准备业务。未实施的共用模块或使用说明不能被本测试方案自身替代。

## G74：一次正式回归

只有第二关口完整通过后，才按获审版本执行本节。工作目录为待测仓库根；须为干净检出。允许代入的变量只有仓库路径、系统临时目录、自动分配的运行目录及已冻结的 `DOC_PATH`。不修改模型、样例、断言、入口、观察方式或判定条件。

先记录并核对产品、方案、判定版本与正式来源；如方案来自另一提交，执行前由正式安装／检出步骤准备审核过的测试内容，禁止在失败后临场补丁。当前方案默认测试与产品同一干净提交。

```sh
git status --porcelain
RUN_DIR=$(mktemp -d "${TMPDIR:-/tmp}/issue74-evidence.XXXXXXXX")
export TMPDIR="$RUN_DIR"
export PYTHONDONTWRITEBYTECODE=1
git rev-parse HEAD > "$RUN_DIR/product-sha.txt"
git log -1 --format=%H -- test-plan/issue-74.md .apm/skills/professor-contact/tests/test_issue74_fixture_support.py > "$RUN_DIR/recipe-sha.txt"
git log -1 --format=%H -- .apm/skills/professor-contact/tests/gate2_evidence.py > "$RUN_DIR/evaluator-sha.txt"
uv --version > "$RUN_DIR/uv-version.txt"
uv run --no-project --python 3.12 python -V > "$RUN_DIR/python-version.txt"
```

`git status` 有任何未提交变更时，停止而不运行。记录 `RUN_DIR` 实际值、开始时间、获审方案提交、需求与计划指针。环境资产：不适用；本地确定性检查不依赖共享运行环境。源码参照基准须可由 `git show` 取得，否则为测试准备无效，不去下载或改用当前代码作参照。

完整回归只执行一次；新增用例和旧第 53、55 号用例都由这一执行拥有，不再另跑定向验收重复证明。完整回归保留已有判定程序自身测试，这是检查完整回归仍包含已冻结判定契约；P74 属于第二关口验证，不能计作一次产品通过。

```sh
uv run --no-project --python 3.12 .apm/skills/professor-contact/tests/gate2_evidence.py --start .apm/skills/professor-contact/tests --pattern 'test_*.py' --require-prefix test_issue74_fixture_support.Issue74FixtureTests. --require-prefix test_issue53_stage4_runtime_assets.Issue53Stage4RuntimeAssetTests. --require-prefix test_issue55_stage3_runtime_assets.Issue55Stage3RuntimeAssetTests. --require-prefix test_gate2_evidence.Gate2EvidenceTests. --out "$RUN_DIR/regression.json" > "$RUN_DIR/regression.stdout" 2> "$RUN_DIR/regression.stderr"
jq '{schema_version,python,cwd,selection,tests_run,started,completed,events,failures,errors,skipped,expected_failures,unexpected_successes,missing_required_prefixes,load_errors,interruption,verdict}' "$RUN_DIR/regression.json"
```

不能只用进程退出码或外层总判定推断全部用例通过。逐个检查 `started`／`completed` 的编号与顺序、对应 `events`、失败／错误／跳过记录，以及要求前缀是否到达；缺少必需新用例不能通过。失败子用例的 `evidence_id` 和详情须保留。完整回归的既有范围外失败保留原记录，按其原要求归属判断，不扩大本议题产品要求或掩盖整轮未就绪。

## 判定、停止和第三关口记录

发现载入错误、参照基准缺失、操作钩子不适用或环境污染时，先按原始事实判断准备／执行无效，不把测试程序问题归为产品失败。正常到达被测操作、且直接断言证明违反本方案对应正式要求时才判产品失败。故障注入本身是合法负例，不因故障输入而把应有拒绝或回滚判定作无效。

启动边界为 `EvidenceResult.startTest` 记录该方法进入：载入前失败为 `CASE_NOT_STARTED`；准备或证据无效为 `INVALID_TEST_EXECUTION`；有效产品失败为 `FAIL`；合法跳过为 `NOT TESTED`；完成且全部断言成立为 `PASS`。本方案无需要外部运行能力的用例，不预设 `BLOCKED` 路径。总判定沿用固定 `classify`；总 `FAIL` 不消除其他用例的无效事实。没有证据文件时记录启动边界与原始错误，不能制造通过结果。

本方案不允许自动重试或因结果不理想重复采样；基础设施故障发生后保存完整尝试并停止，修订或恢复须记录新事实、影响范围及新运行编号。子进程的固定 30 秒限制只用于异常退出观察；整轮预计数分钟，执行者采用可重连进程并保存完整输出，不能后台运行后遗失状态。任何超时或人工终止保存已写证据及原始输出，不产生合并就绪结论。

第三关口逐方法记录用例编号、需求／证明、准确产品／方案／判定版本、运行编号、命令、原始证据位置、结果与理由；S74 单独记录静态产物版本和逐项判断。P74 记录第二关口验证来源，不冒充产品执行。初次没有旧通过来源，全部必需产品用例采用 `EXECUTE_CURRENT`。

以后变化命中以下依赖才改变通过来源：两准备入口及共用模块、路径／目录／写入／摘要语义、业务数据格式、直接导入和命令入口、文档职责、样例初始状态、Python 文件操作观察、固定参照版本、判定程序和证据结构。只改提交编号不自动废除旧结果；仅判定解释变化且旧原始证据完整时选择 `REJUDGE_PRIOR_EVIDENCE`；不受影响时按准确来源和影响分析选择 `REUSE_PRIOR_PASS`；行为、输入或观察事实变化时重新执行受影响用例。

最终条件：三个关口均完整通过、S74 全部满足、所有必需用例对当前版本有效通过、无未解决产品失败或必需用例非通过终态，才能记录合并就绪。作者当前结论：第二关口待审核，第三关口未执行。
