# 第 74 号议题测试方案第 5 版

## 状态与唯一来源

- 修订号：`issue74-test-r5`；本版针对第四版正式通过后、产品提交 `b9b9ec8e81ebee3dfb165ced120690d4f87ade5f` 暴露的一个具体 `false-FAIL` 修复 R2/R3 合法输入证明：实现把内部占用名称编码当作永久保留命名空间，即使没有任何活动占用也拒绝样例根或清单输出。第二关口按 `Test Engineer Rule` §6.2 只重开受影响证明；第三关口结果由产品修复后的正式执行证据决定。冻结文本不等于产品通过。
- 本文件及同一提交的 `.apm/skills/professor-contact/tests/test_issue74_fixture_support.py`、`.apm/skills/professor-contact/tests/test_issue74_cross_run_claims.py`、`test-plan/issue-74-required-cases.json`、`test-plan/issue-74-pass-check.jq` 构成唯一权威方案正文。判定检查样例为同目录的 `issue-74-check-samples.jq` 和 `check-issue-74-pass-check.sh`，注入判定边界样例为 `tests/issue74_recipe_checks.py`（相对于技能目录）。后续修改在本文件合入，更新修订号；不维护评论补丁。
- 本版全部取代第四版 `3ea5d2ab8010787c42c193edad977095145110af` 中冻结的第四版方案内容；第四版全部取代第三版 `df2e23a4cf13d2c477030eb71b24acc9f736dfb1`，第三版全部取代第二版 `589ea76e5f9fb621848439ce965e7fe86a8d83e2`，第二版已取代第一版 `ca1a604d211933ebadf0f53c6d3a351c4356c1b8`；执行不拼接历史方案。第四版曾形成 `Gate 2: PASS + COMPLETE`，该结论仅作为历史记录；本版因已确认的 `false-FAIL` 合法重开受影响 R2/R3 proof，旧结果不再支持当前合并就绪。
- 第五版重开触发事实：批准计划明确规定占用名称的具体编码属于内部实现，并限制“允许收紧的旧输入”仅为已列出的危险类别和并发占用冲突，其他合法输入不得借抽取扩大拒绝范围。当前实现却在 `prepare_root` 和 `ensure_new_output` 中按名称及祖先名称拒绝 `.名称.fixture-claim` 风格路径，即使没有活动占用；第四版 40 个必需方法不会拒绝这一实现，因此会错误接受一个会拒绝合法输入的产品版本。
- 取代范围：第 74 号议题正文的“测试安排草案”和第四版测试方案。不取代需求、已批准执行计划或历史原始测试证据。
- 正式需求：[第 74 号议题需求第 1 版](https://github.com/ScholarWorkflow/professor-contact/issues/74)，读取更新时间 `2026-10-02T16:02:24Z`；决定人为议题记载的项目负责人。
- 执行计划：[第三版](https://github.com/ScholarWorkflow/professor-contact/blob/a328e788a21af8fc7d3ebf052c399054d242b786/plan/issue-74.md)。计划审核来源为项目工作目录《第75号拉取请求-第三版执行计划复审-2026-10-03.md》，批准只覆盖实施；第四版的 live claim 反例和本版的名称误拒绝都由该计划原有的隔离、兼容与允许收紧边界覆盖，不重开计划审核。
- 兼容基准：`768b49ef4514e36edec6b57ed3821a99af9e9c00`。测试读取该固定提交的两个旧入口作为合法成功结果的独立参照，不用当前共用工具生成预期值。
- 当前已知产品实现为 `b9b9ec8e81ebee3dfb165ced120690d4f87ade5f`；该实现修复了 live claim 被其他运行当作样例根的问题，但增加了未经计划授权的按名称永久拒绝。后续本地执行 agent 修复产品后，以修复提交作为新的产品版本，并按下文 G74 重新执行。测试方案、产品和判定提交分别记录。
- 全量回归采用 `ABSOLUTE_PASS`：全部有效方法必须通过。基线同样失败不能抵消当前失败；本版不采用失败后改为无新增回归的判定。
- 方案和判定版本：审核者须绑定包含本文件和测试文件的准确提交；判定入口为该获审版本的 `tests/gate2_evidence.py`。执行前核对文件内容与获审版本一致。产品、方案、判定提交可以不同，分别记录。
- 规则来源：项目正式 `PROJECT_CONSENSUS.md`、`Test Engineer Rule.md`，以前者为准。规则文件在项目工作目录，不把草稿复制为本仓库规范。

## 范围和证明归属

所有路径在下表中相对于 `.apm/skills/professor-contact/`。新增测试类为 `test_issue74_fixture_support.Issue74FixtureTests` 与 `test_issue74_cross_run_claims.Issue74CrossRunClaimTests`。每个方法是一个用例；方法内子用例只区分会改变行为的条件。测试作者负责设计，执行者保存证据，审核者判断有效性；作者不替独立审核者宣布第三关口通过。

| 要求／证明 | 唯一负责者和用例 | 直接观察事项 |
| --- | --- | --- |
| R2：成功结果兼容 | `test_compatibility_bytes_manifest_hashes_and_returns` | 固定旧版本与当前版本在同一路径下的返回对象、全部文件字节一致；摘要由标准库独立重算；原包装返回保留；禁止输出缺席。实际共用三类操作由 S74 的完整源码调用链独立证明，不按某个内部摘要函数或调用栈格式判断 |
| R2：命令和按文件加载两种方式 | `test_cli_from_unrelated_directory_without_pythonpath` | 按文件加载用于所有新增用例；两个旧脚本从无关目录直接启动，不设置 `PYTHONPATH`；成功退出及结构化字段保持原约定；失败退出为 1、状态为 `error`，既有文件字节不变 |
| R2/R3：内部占用名称不得扩大合法路径拒绝范围 | `test_issue74_cross_run_claims.Issue74CrossRunClaimTests.test_claim_like_paths_without_live_claim_remain_legal` | 第 53、55 号两个受支持入口分别验证四种没有活动占用且无其他危险条件的合法输入：样例根自身使用 `.ordinary.fixture-claim` 风格名称、样例根位于该风格祖先目录下、清单输出自身使用该风格名称、清单输出位于该风格祖先目录下。四种都必须正常生成样例和清单；不能只因内部编码样式拒绝 |
| R3：预先拒绝危险路径与清单冲突 | `test_preexisting_conflicts_fail_before_any_sample_write` | 两入口的文件根、非空根、已有文件／目录清单、清单与样例重合、生产者内根／输出，以及第 53 号第二个根的对应拒绝类别：原字节保留，未创建其他样例；保持旧 `FixtureBuildError` 通道 |
| R3：第 53 号双根独立 | `test_equal_and_nested_issue53_roots_are_rejected_without_changes` | 根相等、两种祖先关系均拒绝；根和清单未创建 |
| R3：已有空目录不删除重建 | `test_existing_empty_root_identity_is_preserved` | 已有目录设备编号与目录编号保持；不得调用删除该目录的操作 |
| R3：不同运行独立 | `test_different_runs_do_not_share_writable_outputs` | 两次独立分配后，修改右侧文件，左侧全部字节不变 |
| R3：同一解析路径占用、正常释放 | `test_overlapping_call_cannot_recreate_first_empty_root` | 第一调用取得空根、首次写入前，第二调用经符号链接指向同一真实根；第二调用拒绝，原目录编号保留、第二输出缺席；第一调用成功；父目录无残留占用 |
| R3：不同真实路径不得共享正在使用的占用目录 | `test_issue74_cross_run_claims.Issue74CrossRunClaimTests.test_live_claim_directory_cannot_be_used_as_another_run_root` | 第一调用已取得占用且尚未写样例时，从隔离目录的真实文件系统状态找到其空占用目录，不依赖占用名称编码；第二调用以该实际占用目录作为自己的样例根，必须在写入前通过原 `FixtureBuildError` 通道拒绝，不能改变该占用目录、创建第二调用清单或资料根；第一调用随后正常完成并释放自身占用。第 53、55 两入口均作为子用例执行 |
| R3：清单检查后的创建冲突 | `test_manifest_creation_race_preserves_competing_bytes_and_partial_samples` | 清单实际打开前插入其他调用字节；写入失败且不覆盖竞争者；本次部分样例仍存在，占用释放 |
| R3：第 53 号第二根失败回滚 | `test_second_root_failure_rolls_back_only_new_owned_first_root` | 第二根创建失败：本次新建第一根删除；调用前已有空根保持原目录编号；被替换的第一根及其新内容保留；无清单或遗留占用 |
| R3：写入失败保留部分样例 | `test_sample_write_failure_preserves_partial_samples` | 资料写入故障发生后，已写 `info.json` 保留、清单缺席、占用释放 |
| R3：异常占用拒绝接管 | `test_abrupt_exit_leaves_occupation_and_next_call_cannot_take_over` | 子进程在首次写入前以 91 退出，跳过正常释放；占用保留；下一调用拒绝且不改变文件或路径集合 |
| R4：产品失败、准备无效、空执行分类 | P74：既有 `test_gate2_evidence.Gate2EvidenceTests` 的判定通道验证 | 有效成功为 `PASS`；有效产品断言或调用失败为 `FAIL`；准备无效、空执行、缺少证明等保持对应非通过终态；产品失败不会被后续清理错误掩盖 |
| R1 归属、虚构数据和非目标；R2 实际复用；R4 文档职责与使用方法 | S74：下文固定源码与文档检查 | 共用模块位于生产者测试目录；两入口在合法成功路径实际调用共用目录、写入、摘要操作；虚构业务数据由调用方拥有；差异仅在计划允许范围；使用说明区分准备／执行／判定／业务样例，给出新增样例、独立目录、异常占用清理及实际运行步骤 |
| 两入口现有业务验收兼容 | G74：一次完整回归中的既有 `test_issue53_stage4_runtime_assets`、`test_issue55_stage3_runtime_assets` | 沿用这两个版本化测试的原断言，禁止为本次迁移降低判定条件 |

兼容字节用例分别覆盖根外清单和合法根内新清单，防止一律拒绝根内输出。只比较固定同一路径的字节；路径文本属于生成内容，不能把不同路径产生的字节差异当作回归。独立摘要比较不调用被测 `sha256` 作为唯一参照。

普通目录名称和虚构教授名称在共享操作与判定相同时仍为等价输入，不机械枚举。`.ordinary.fixture-claim` 风格名称不再归入“普通名称等价类”，因为当前实现已经证明它会触发专门分支；本版只固定能区分该专门分支的最小四种路径表面，不扩大到其他任意字符串。业务状态字段由固定基准和第 53、55 号旧测试负责。生产者真实检出不作为危险写入目标：目录拒绝用例在入口实际加载的 `support` 模块对象上，把 `producer_root` 的返回前提替换为隔离空间内的虚构生产者；路径保护逻辑和业务数据保持原样。该前提由最小检查确认实际消费，不能替换未被调用的入口包装函数。不新增真实代理、浏览器、文献服务或安装测试：这些调用链未变化，且当前要求由生产者本地确定性检查证明。

## 输入、隔离和故障注入

固定解释器为通过 `uv run --no-project --python 3.12` 取得的 CPython 3.12；无额外包。记录实际补丁版本，不能只写预期版本。测试子进程使用同一 `sys.executable`。基准源码在内存加载，真实入口在当前生产者按文件加载；本轮不是安装证明，不创建或修补消费者。

每个方法在 `TMPDIR` 下创建独占 `TemporaryDirectory`，拒绝位于生产者内的临时空间。所有路径、符号链接、竞争者内容、替换目录和异常进程均属于该隔离空间。测试结束整体清理自有空间，不连接真实用户目录或状态；故障前后的必要字节和路径关系由断言纳入结构化事件。这里整体清理测试自有空间不等于授权被测准备工具清理遗留占用。

样例写入故障、重叠占用、跨运行占用目录碰撞和异常退出固定在第一调用的 `Path.open` 写入边界，第二根创建故障固定在 `Path.mkdir` 边界；清单竞争固定在实际 `os.open` 创建前，使用保存的原始操作排他创建竞争文件，再调用原始被测创建操作，不替代其返回或排他语义。跨运行 live claim 用例在第一调用已经取得占用且首次样例写入尚未发生时，从该独占隔离父目录枚举实际存在的空占用目录，排除正式样例根后选择真实占用作为第二调用的根；不调用 `claim_path_for`，不假定 `.fixture-claim` 或其他占用名称。第二调用使用完整受支持准备入口，不能用 helper 直接调用代替。只控制竞争顺序或一次操作故障，不重写业务输入、不代替调用方执行传递。不以内部函数名称或调用栈格式作为验收条件。声明的 `Path.open` 交错点未被真实到达，或隔离状态无法唯一识别应有数量的占用目录时，测试抛出 `TestPreparationError`，属于执行无效；不将观察程序失效认定为产品失败。

第五版合法名称用例不创建第一运行、不制造活动占用，也不调用内部占用路径 helper；它只在测试自己的独占临时目录中选择 `.ordinary.fixture-claim` 风格的样例根或清单路径，并保持生产者归属、目录类型、目录内容、双根独立和输出新建等其他前提合法。入口正常返回且对应样例与清单实际生成才通过；任何仅由名称或祖先名称触发的拒绝都是产品 `FAIL`，不是测试准备无效。

异常退出子进程最多运行 30 秒，超时保存原始诊断并以 `TestPreparationError` 标为执行无效；不重试。实际故障进程应由 `subprocess.run` 的超时处理结束，本用例不启动孙进程。

## P74：第二关口的执行前检查

第三版已完成的判定程序四方法、注入异常边界四样例、完整性六样例及观察器四方法在本版保持源码和语义不变。第四版跨运行 live claim 用例和第五版合法名称用例都是 producer-local deterministic test，不依赖真实安装、runtime wiring、代理、MCP、浏览器、外部进程或第三方运行时，因此不新增 Runtime Preflight。live claim 用例复用第三版已经确认可观察的 `Path.open` 首次样例写入边界；第五版合法名称用例没有注入或外部观察假设，只检查两个正式准备入口的直接返回和文件系统结果，不增加 parser 或 evaluator。

以下命令从仓库根运行；当判定程序、观察器或其依赖未变化时，可按准确历史来源复用第三版检查，不重复执行。若相关依赖变化，则先使用下节的目录分配与版本记录步骤，再执行：

```sh
uv run --no-project --python 3.12 .apm/skills/professor-contact/tests/gate2_evidence.py --start .apm/skills/professor-contact/tests --pattern test_gate2_evidence.py --require-prefix test_gate2_evidence.Gate2EvidenceTests. --out "$RUN_DIR/preflight.json" > "$RUN_DIR/preflight.stdout" 2> "$RUN_DIR/preflight.stderr"
jq '{schema_version,python,selection,tests_run,started,completed,events,load_errors,interruption,verdict}' "$RUN_DIR/preflight.json"
uv run --no-project --python 3.12 .apm/skills/professor-contact/tests/gate2_evidence.py --start .apm/skills/professor-contact/tests --pattern issue74_recipe_checks.py --contains issue74_recipe_checks.Issue74RecipeChecks. --require-prefix issue74_recipe_checks.Issue74RecipeChecks. --out "$RUN_DIR/recipe-checks.json" > "$RUN_DIR/recipe-checks.stdout" 2> "$RUN_DIR/recipe-checks.stderr"
jq '{schema_version,python,selection,tests_run,started,completed,events,load_errors,interruption,verdict}' "$RUN_DIR/recipe-checks.json"
sh test-plan/check-issue-74-pass-check.sh "$RUN_DIR/completeness"
jq -e 'length == 6 and all(.matched == true)' "$RUN_DIR/completeness/results.json"
uv run --no-project --python 3.12 .apm/skills/professor-contact/tests/gate2_evidence.py --start test --pattern test_issue74_recipe_observers.py --out "$RUN_DIR/observers.json" > "$RUN_DIR/observers.stdout" 2> "$RUN_DIR/observers.stderr"
jq '{tests_run,started,completed,events,verdict}' "$RUN_DIR/observers.json"
```

需完整读取全部样例及结果；三个原有检查模块各恰好完成四个规定方法，且没有产品方法被发现或执行。记录三种通道、失败后清理／中断仍保留失败、空执行与缺少证明不能通过的结果。错误实现仅在最小非验收检查内部临时替换，离开上下文恢复；不用于正式产品验收。检查失败时暂停依赖该判定程序的验收，分析是判定程序、检查样例或环境问题。未变化检查采用准确历史来源复用，不重复执行。

官方依据：[CPython 3.12 文件操作](https://docs.python.org/3.12/library/pathlib.html#pathlib.Path.open)、[结构化测试结果](https://docs.python.org/3.12/library/unittest.html#unittest.TestResult)。这些依据说明接口，不证明迁移实现的业务结果；正式 verdict 仍由实际验收执行产生。

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

1. 共用模块只负责目录、文件和摘要；完整阅读两个 `build_fixture` 的合法成功调用链，分别记录每项操作到共用模块的准确文件与位置，确认不是仅导入、未调用或仍由入口独立完成。虚构数据仍由两调用方拥有；没有启动浏览器、外部服务、代理或读取用户资料的路径。另阅读占用路径生成及冲突检查、释放和归属检查，确认占用不与根、样例或清单重合，未取得占用者不清理他人状态；一个运行仍持有的占用目录不能被另一运行作为不同样例根写入；占用名称编码只用于定位真实占用，不能在没有活动占用或其他冻结危险条件时把同名样式的普通路径永久划为禁用命名空间。
2. 没有迁移范围外准备入口，没有修改业务程序、状态接口、代理配置或其他议题的验收断言。判定程序保持产品失败优先、空执行非通过；如确有变化，先分析影响并修订方案，不静默复用。
3. 使用说明区分四项职责，包含旧入口参数、如何新增议题专属样例、如何执行并按结构化结果判断、独立目录分配、异常占用不得自动接管及隔离空间整体清理责任；说明不得把内部占用名称编码写成超出批准计划的永久用户路径限制。

静态产物是证据正文，审核记录是其语义判断；不以文件存在、关键词命中或作者“已完成”代替上述检查。S74 是实现范围和文档证明，不重复运行准备业务。未实施的共用模块或使用说明不能被本测试方案自身替代。

## G74：一次正式回归

只有第二关口完整通过后，才按获审版本执行本节。工作目录为待测仓库根；须为干净检出。允许代入的变量只有仓库路径、系统临时目录、自动分配的运行目录及已冻结的 `DOC_PATH`。不修改样例、断言、入口、观察方式或判定条件。

先记录并核对产品、方案、判定版本与正式来源；如方案来自另一提交，执行前由正式检出步骤准备审核过的测试内容，禁止在失败后临场补丁。产品修复和第五版 Recipe 可以位于不同提交，分别记录准确提交。

```sh
git status --porcelain
RUN_DIR=$(mktemp -d "${TMPDIR:-/tmp}/issue74-evidence.XXXXXXXX")
export TMPDIR="$RUN_DIR"
export PYTHONDONTWRITEBYTECODE=1
export UV_CACHE_DIR="$RUN_DIR/uv-cache"
git rev-parse HEAD > "$RUN_DIR/product-sha.txt"
git log -1 --format=%H -- test-plan/issue-74.md .apm/skills/professor-contact/tests/test_issue74_fixture_support.py .apm/skills/professor-contact/tests/test_issue74_cross_run_claims.py test-plan/issue-74-required-cases.json test-plan/issue-74-pass-check.jq > "$RUN_DIR/recipe-sha.txt"
git log -1 --format=%H -- .apm/skills/professor-contact/tests/gate2_evidence.py > "$RUN_DIR/evaluator-sha.txt"
uv --version > "$RUN_DIR/uv-version.txt"
uv run --no-project --python 3.12 python -V > "$RUN_DIR/python-version.txt"
```

`git status` 有任何未提交变更时，停止而不运行。记录 `RUN_DIR` 实际值、开始时间、获审方案提交、需求与计划指针。`UV_CACHE_DIR` 由独立运行目录分配，仅是依赖缓存位置，不改变解释器、输入或断言。环境资产：不适用；本地确定性检查不依赖共享运行环境。源码参照基准须可由 `git show` 取得，否则为测试准备无效，不去下载或改用当前代码作参照。

第五版合法重开新增 1 个产品方法，且当前产品修复还会改变共用占用处理；第四版整轮结果不能直接充当第五版完整 G74。产品修复后完整回归重新执行一次；新增合法名称用例、live claim 用例和旧第 53、55 号用例都由这一执行拥有，不再另跑定向验收重复证明。完整回归保留已有判定程序自身测试，这是检查完整回归仍包含已冻结判定契约；P74 属于第二关口验证，不能计作一次产品通过。

```sh
uv run --no-project --python 3.12 .apm/skills/professor-contact/tests/gate2_evidence.py --start .apm/skills/professor-contact/tests --pattern 'test_*.py' --require-prefix test_issue74_fixture_support.Issue74FixtureTests. --require-prefix test_issue74_cross_run_claims.Issue74CrossRunClaimTests. --require-prefix test_issue53_stage4_runtime_assets.Issue53Stage4RuntimeAssetTests. --require-prefix test_issue55_stage3_runtime_assets.Issue55Stage3RuntimeAssetTests. --require-prefix test_gate2_evidence.Gate2EvidenceTests. --out "$RUN_DIR/regression.json" > "$RUN_DIR/regression.stdout" 2> "$RUN_DIR/regression.stderr"
REGRESSION_EXIT=$?
printf '%s\n' "$REGRESSION_EXIT" > "$RUN_DIR/regression-exit.txt"
jq '{schema_version,python,cwd,selection,tests_run,started,completed,events,failures,errors,skipped,expected_failures,unexpected_successes,missing_required_prefixes,load_errors,interruption,verdict}' "$RUN_DIR/regression.json"
jq --slurpfile required test-plan/issue-74-required-cases.json -f test-plan/issue-74-pass-check.jq "$RUN_DIR/regression.json" > "$RUN_DIR/complete-pass.json"
jq -e '. == true' "$RUN_DIR/complete-pass.json"
```

不能只用进程退出码或外层总判定推断全部用例通过。41 个必需方法编号由同提交的 `issue-74-required-cases.json` 固定：13 个第 74 号产品验收方法、24 个既有第 53／55 号方法、4 个既有判定方法。通过检查必须为 `true` 且回归退出码为 0；只验证类名前缀不够。程序按结构化字段确认执行数、唯一编号、开始与完成顺序、全部错误和跳过记录，以及全部必需方法存在，不要求不同合法运行采用同一排序。非通过时完整保留记录，逐方法按固定 `classify` 的字段规则判断；完整性检查仅确认是否全部通过，不改写产品失败或其他终态。失败子用例的 `evidence_id` 和详情须保留。完整回归的既有范围外失败按其原要求归属判断，不扩大本议题产品要求或掩盖整轮未就绪。

## 判定、停止和第三关口记录

发现载入错误、参照基准缺失、操作钩子不适用、无法从隔离状态识别应有占用目录或环境污染时，先按原始事实判断准备／执行无效，不把测试程序问题归为产品失败。正常到达被测操作、且直接断言证明违反本方案对应正式要求时才判产品失败。故障注入和受控并发交错本身是合法负例，不因输入冲突而把应有拒绝或回滚判定作无效。第五版合法名称用例不依赖故障注入；其输入满足正式前提而被入口拒绝时直接归为产品 `FAIL`。

启动边界为 `EvidenceResult.startTest` 记录该方法进入：载入前失败为 `CASE_NOT_STARTED`；准备或证据无效为 `INVALID_TEST_EXECUTION`；有效产品失败为 `FAIL`；合法跳过为 `NOT TESTED`；完成且全部断言成立为 `PASS`。本方案无需要外部运行能力的用例，不预设 `BLOCKED` 路径。总判定沿用固定 `classify`；总 `FAIL` 不消除其他用例的无效事实。没有证据文件时记录启动边界与原始错误，不能制造通过结果。

本方案不允许自动重试或因结果不理想重复采样；基础设施故障发生后保存完整尝试并停止，修订或恢复须记录新事实、影响范围及新运行编号。子进程的固定 30 秒限制只用于异常退出观察；整轮预计数分钟，执行者采用可重连进程并保存完整输出，不能后台运行后遗失状态。任何超时或人工终止保存已写证据及原始输出，不产生合并就绪结论。

第三关口逐方法记录用例编号、需求／证明、准确产品／方案／判定版本、运行编号、命令、原始证据位置、结果与理由；S74 单独记录静态产物版本和逐项判断。P74 记录第二关口验证来源，不冒充产品执行。第四版 live claim 用例和第五版合法名称用例都没有可支持当前产品版本的历史 PASS，采用 `EXECUTE_CURRENT`；由于产品修复将改变共用占用行为，第五版 G74 按上节重新完整执行，不把第三版或第四版整轮结果改写为当前执行。

以后变化命中以下依赖才改变通过来源：两准备入口及共用模块、路径／目录／占用／写入／摘要语义、业务数据格式、直接导入和命令入口、文档职责、样例初始状态、Python 文件操作观察、固定参照版本、判定程序和证据结构。只改提交编号不自动废除旧结果；仅判定解释变化且旧原始证据完整时选择 `REJUDGE_PRIOR_EVIDENCE`；不受影响时按准确来源和影响分析选择 `REUSE_PRIOR_PASS`；行为、输入或观察事实变化时重新执行受影响用例。

最终条件：三个关口均完整通过、S74 全部满足、所有必需用例对当前版本有效通过、无未解决产品失败或必需用例非通过终态，才能记录合并就绪。正式结果不得从方案通过推断。

## 第四版重开与第二关口修复记录（历史）

第四版重开触发满足 `Test Engineer Rule` §6.2：冻结要求为第三版计划的占用隔离与“不同真实路径的运行不共享可写状态”；原负责 Proof 为 R3 的不同运行独立／同路径占用两个用例；最小反例是第一运行的 live claim 路径作为第二运行不同 root 时，第三版 Recipe 会让 39 个必需方法全部通过，因此存在明确 `false-PASS`。

第四版只新增一个 R3 产品用例并更新必需编号、G74 命令和相应文字说明；R1、R2、R4 的 proof owner、既有 11 个第 74 号验收方法、P74 判定程序、完整性检查程序和观察器源码均未改。新用例直接通过两个受支持准备入口执行，动态读取隔离目录状态获取 live claim，不固定内部占用命名；满足要求的实现可在任何样例写入前拒绝，违反要求的实现会产生产品 `FAIL`，无法到达预定交错点或无法识别占用状态时为 `INVALID_TEST_EXECUTION`。

第三版 P74 证据在第四版可复用：判定入口和三个判定通道未变；新增用例是 producer-local deterministic test，不依赖第 3.2 节列出的 runtime／fixture／外部观察假设；其 `Path.open` 写入交错点已由第三版同一类用例的当前源码与观察检查确认。新增 required-case ID 后，`issue-74-check-samples.jq` 从 `$required` 动态构造样例，`issue-74-pass-check.jq` 也按 `$required` 动态判断，不存在固定 39 的 parser 假设。

第四版当时按第 3.3 节重新检查完整 Gate 2 记录并得到历史结论：`Test Engineer Gate 2: PASS`、`Gate review completeness: COMPLETE`。该结论已被本第五版合法重开，不作为当前 Gate 2 来源。

## 第五版重开与第二关口修复记录

重开满足 `Test Engineer Rule` §6.2 的具体事实如下：

- 正式要求：第三版批准计划的“允许收紧的旧输入仅为上述拒绝类别和并发占用冲突；其他合法输入不得借抽取扩大拒绝范围”，以及“占用名称的具体编码属于内部实现”。
- 原负责 Proof／Case：R2 成功兼容、R3 不同运行隔离、第四版 live claim 用例。它们证明真实活动占用必须拒绝，但没有证明名称样式本身不能成为新的拒绝条件。
- 最小错误结果：在没有第一运行、没有活动占用、目标位于测试隔离空间且满足目录／输出其他全部合法前提时，把样例根设为 `/tmp/.../.ordinary.fixture-claim`。当前 `b9b9ec8` 会仅因名称匹配内部编码而以 `FixtureBuildError` 拒绝；第四版 40 个必需方法仍可全部通过，因此存在明确 `false-FAIL` 漏审。

本版只在既有 `Issue74CrossRunClaimTests` 增加一个产品方法，并把 required-case ID 从 40 个更新为 41 个；没有修改判定程序、完整性检查程序、第三版既有观察器或正式执行入口。新增方法通过两个正式准备入口直接执行，并以四个子用例区分根／输出以及自身名称／祖先名称四个实际被当前实现分别检查的路径表面；其余前提保持合法。满足要求的实现正常生成样例和清单即 `PASS`；仅由名称触发拒绝的实现为产品 `FAIL`；不存在需要把产品拒绝降级为测试准备无效的外部观察条件。

P74 的历史检查可继续复用：判定入口、结构化字段、parser、完整性脚本及异常注入边界均未变化。新增方法是 producer-local deterministic test，没有第 3.2 节列出的 runtime、fixture、外部 process、browser 或 attribution 假设，不新增 Runtime Preflight。`issue-74-check-samples.jq` 和 `issue-74-pass-check.jq` 仍从 `$required` 动态消费必需编号，不存在固定 40 的判断。

按第 3.3 节重新检查修改后的完整 Gate 2 记录：每项冻结要求均有唯一 proof owner；41 个必需方法中新增方法只负责“内部占用名称不扩大合法输入拒绝范围”；输入、证据、停止条件和 verdict 已固定；live claim 的拒绝证明与无 live claim 的合法接受证明相互区分；没有把实现细节名称本身升级成产品要求，也没有新增重复正式业务调用来证明同一事实。

`Test Engineer Gate 2: PASS`

`Gate review completeness: COMPLETE`

第三关口当前为 `NOT_READY`：当前产品实现 `b9b9ec8e81ebee3dfb165ced120690d4f87ade5f` 按名称永久拒绝合法根／清单路径，且使用说明也把该未批准限制写成正式行为。本轮测试工程师只修 Recipe 和验收用例，不修改产品实现或产品说明，也不运行正式验收。下一步由本地执行 agent 按已批准第三版计划删除名称本身的永久拒绝，同时保留“真实活动占用目录不得被另一运行接管”的保护；修复后按第五版一次执行 G74 和 S74，41 个必需方法全部有效通过且 S74 满足后，才能重新记录 `Gate 3: PASS` 与合并就绪。
