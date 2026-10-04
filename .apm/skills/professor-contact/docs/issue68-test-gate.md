# 第 68 号议题：测试关口修复记录

本文件是完整后继记录的候选稿。它不冒充验收决定人批准，也不把步骤验证或合成事件测试当作正式运行通过。正式第一关口后继和第十版计划获批后，审核者可用本文件统一发布第二关口，不需要拼接旧评论。

> 2026-10-04 取代声明：本文件的 `PC68-R1` 执行条款已被后继记录 `issue-68-gate2-r12-2026-10-04`（`docs/issue68-test-gate-r12.md`）取代：正式入口改为 `run_issue68_stage5_routing_r12.py`（取代本文第 74、79 行的 r11 入口命令）；Codex 请求模型按当前项目共识 `PROJECT_CONSENSUS.md`（更新时间 2026-10-04 14:41）为 `gpt-6-luna` + `model_reasoning_effort="low"`（取代本文第 97 行附近"构建固定 `gpt-5.6-luna`"条款及其 r11 构建器断言）。以下历史文本保留原状，仅作 r10/r11 时代记录，不再作为 `PC68-R1` 的执行来源。

## 当前输入与取代关系

| 项目 | 版本或来源 |
| --- | --- |
| Requirement revision | `2026-09-29 user requirement — per-professor state at every stage`，加 2026-10-01 独立合并澄清 |
| Frozen Acceptance Contract revision | 已发布：`issue-68-gate1-r1-2026-09-29`；候选修正：`issue-68-gate1-r2-2026-10-02` |
| Canonical Plan revision | `issue-68-plan-r10-2026-10-01`，正式批准待定 |
| Target repository revision | 执行时指定完整 `PRODUCER_SHA`，必须与干净检出的 `HEAD` 相同；原审 head 为 `656f02d7259cd10acb36fc1d183e78757f770aab` |
| 已发布第一关口 | [第一版](https://github.com/ScholarWorkflow/professor-contact/issues/68#issuecomment-5890058133) |
| 已发布第二关口 | [第九版](https://github.com/ScholarWorkflow/professor-contact/issues/68#issuecomment-5895563842) |
| 候选第二关口 | `issue-68-gate2-r10-2026-10-02`，本文件 |
| 验收决定人 | `RekiDunois`，议题作者 |
| 当前计划 | [第十版完整计划](https://github.com/ScholarWorkflow/professor-contact/issues/68#issuecomment-5928429591) |
| 要求澄清 | [三个问题独立合并](https://github.com/ScholarWorkflow/professor-contact/pull/71#issuecomment-5926356852) |

候选第二关口发布后，`supersedes` 为 `issue-68-gate2-r9-2026-09-30` 及其已经取代的 r1–r8、议题正文旧 T68 方案。失效历史评论为 5890556251、5891284891、5891489465、5891774001、5893223498、5894871114、5895250398、5895563842。发布前，第九版仍是唯一已发布第二关口；其受影响证明不能直接用于当前修订。

旧 P7 的“仅按本地 email_id 过滤”步骤由目录与编号共同归属的证明替代；旧总览登记断言和人工修改登记样例由自身正文哈希断言替代；旧四个不存在的运行脚本由 `tests/runtime/` 下同名脚本实现替代。仍只有 `PC68-D1`、`PC68-R1` 两个用例。第十版计划取代第九版评论 5928210478、5928341762，第八版正文及评论 5928081729；不能把它们的批准结论移给第十版。

## 冻结验收约定候选修正

第一关口 r2 保留 r1 的 R68-1–R68-7、AD68-1、AD68-3、AD68-4、范围、兼容和禁止副作用。正式来源仍为第 68 号要求、第 59 号定向单邮件约定、第 67 号教授本地包生产及迁移约定、项目共识；第 67 号有效方案截至 r18 取代旧 r2/r3 指针。

唯一撤销项是把第 48 号实现或证明先通过当作当前问题合并前提。独立合并澄清明确撤销该前提。AD68-2 的候选表述为：第 68 号不得复制通用写锁；第五阶段总览不读写 `_contact_projections.json`，使用总览自身 `managed_by`、`render_sha256` 保护人工修改，一次原子写入完整文件；通用跨进程写锁仍归第 48 号拥有，其他问题的合并状态不成为本问题验收条件。

第十版计划对 AD68-4 的候选解释是 `(canonical professor_dir, email_id)`，不改编号公式：显式目录先归属；旧格式先计算原始候选，唯一候选必须参与重复检查，多候选才排除已显式满足的教授；错误只影响其归属教授。该解释及总览方案等待计划审核者批准，本文不增加新的业务要求。

## 重开与最小修正

`Reopen trigger`：已接受独立合并澄清；第十版目录归属、总览保护方案及当前实现、测试和证据程序变化。只重开 AD68-2、P5、P7、R1 及直接依赖。其他第九版证明设计保留原来源，不开展无关优化。

| 修改 | 规则、缺陷、错误判定风险与最小修正 | 受影响证明与第三关口决定 |
| --- | --- | --- |
| M1 | 测试规则 §1、§6.2：r1 仍含先合并前提，会错误拒绝独立可合并的请求；统一记录撤销条款及批准状态 | AD68-2；正式冻结、计划批准前不宣布通过 |
| M2 | §2 禁止副作用、§3.3：旧测试要求共享登记，拒绝正确实现并遗漏共享文件读写；改为独立哈希、读写拦截、字节保留断言 | R68-5、AD68-2、D1/P5；执行当前版本 |
| M3 | §2 合法上游样例、直接证据：旧 B 包编号与伪造 scope 不一致，且仅检查 A，无法证明碰撞归属；用编译器生成同名同编号的两个真实本地包，检查两个 owner 的 plan/finalize/wrapper；修正两阶段解析 | AD68-4、D1/P7；执行当前版本 |
| M4 | §3.1–3.3：七项证明和四个运行入口缺失，真实转发和判定链不可执行；补固定程序、完整 scope 转发证据、三个判定通道及原生顺序解析 | D1 的固定入口、R1；当前执行；合成检查不复用为运行通过 |

当前真实步骤验证另发现 R1 直接依赖的两个问题。运行器会先注入环境说明形式的 user 消息，不能以全部 user 消息数量作为业务输入数量；解析程序改为定位含 `email_pack` 的业务对象，同时支持当前版本正式 commandExecution 的 shell 包装。用原始完整证据重新判读发现 root 把 `DISCOVERED_BY_WORKFLOW` 作为包路径、用范围占位串委派，没有执行本应由 root 负责的只读解析；正确判定为 `FAIL_PRODUCT`，不能写成运行器不可观察。最小产品修正把第五阶段的输入解析责任放到调用入口，并明确真实路径、完整范围和原样选择必须在委派前形成；generator 保持单教授职责并使用项目要求的单条 JSON 结果协议。只影响 R1，不改变 D1 的已通过业务实现。

后续 `3ff9f83` 的有效原生执行又提供两个最小反例：A 的子代理把真实目录 `試験 教授` 改成 `试验 教授`，错误返回缺包；B 按正式代理要求先执行不带结果和选择的 plan，缺核验时合法返回 `needs_input / verify_missing_contact_email`。旧判定把二者都隐藏为缺观察。前者违反目录身份保真，最小产品修正要求从原包取目录、原样传入命令和结果；有完成 JSON 却目录不符须判 `FAIL_PRODUCT`。后者暴露预检查与正式第一步不同：带结果的预检查拒绝码不等于代理的最终拒绝码。最小步骤修正同时归档实际初始 plan 的缺核验结果，保留带结果 plan 的硬门禁检查；R1 只检查真实未完成结果原样返回，不把核验交互的原因枚举变成新业务门禁。主代理改写已返回结果、子代理把缺核验当成功均判 `FAIL_PRODUCT`。依据测试规则 §2、§3.1、§3.3：分别避免错误通过、错误拒绝和将有效失败误归观察阻断。只重开 R1 的路径、结果和预检查；须执行当前安装的受影响步骤，不能复用旧失败为通过。

`ab497f3` 复验仍错误改写 A 的目录，文字提醒不足。实际加载的当前 agent 身份和定义已在共享诊断中确认，但该诊断不承担通过判定。最小后续修正为程序传递同一业务对象的临时 JSON 副本：root 从实际发现字段序列化副本，原生 payload 仍包含完整未改的包、选择和范围，另带副本路径；owner 解析副本字段组成 subprocess 参数列表及最终目录，不手写含非 ASCII 字符的身份。不是新的事实源、runner 命令或原生 API 参数。只有 R1 的传递步骤变化，D1 不受影响。

`REVIEW_DEFECT`：`1fff765` 的有效完整运行已正确传递两份包、完整选择和范围，子代理保留目录、返回未完成结果，root 等待并原样消费；但新增的判定要求在运行后读取临时副本，实际副本已不可读，错误产生 `BLOCKED_OBSERVABILITY / owner_input_copy_unobservable`。违反测试规则 §3.1 证据来源与 §3.3 唯一证明负责者：R1 的正式来源是完成的原生消息，实际 runner 消费归 D1/P7；没有临时副本必须长于请求存活的产品要求。最小修正撤销该额外文件寿命依赖，仍逐字段检查原生 payload；保留无副本文件但正式消息完整的判定回归。受影响仅 R1 解析，不修改生产代码或重采样；使用该完整原始运行重新判读，来源仍标记 `1fff765`，不冒充新提交执行。尚无正式 `PASS + COMPLETE` 可撤销。

`Reused proof / PASS`：第九版 P1–P4、P6 的设计未受这两项产品修正影响，沿用其要求和断言；没有正式第三关口 PASS 可复用，`N/A`。原 PR 的 828 项自测不升级为正式第三关口证明。`Affected Gate 3 cases`：D1、R1；运行输入、scope 和解析已变化，不用旧运行替代。

## 唯一证明负责者

| 要求 | 负责证明 | 直接检查 |
| --- | --- | --- |
| R68-1、R68-6 无旧包兜底 | D1/P1 | 合法本地与冲突旧包结果一致；缺本地包时旧包不能兜底；零状态和渲染写入 |
| R68-2、R68-7 本地精确范围 | D1/P2 | 选中邮件先解析；未选畸形行无关；选中非法输入拒绝且无部分写入 |
| R68-3 | D1/P3 | 本地批量只消费 A；同教授缺失、重复拒绝 |
| R68-4、R68-7 状态隔离 | D1/P4 | A 提交后 B 失败不改 A 字节；校验记录只改指定本地状态 |
| R68-5、修正 AD68-2 | D1/P5 | finalize 不触总览；重建自身哈希、幂等、人工修改保护；共享登记访问拦截及字节不变 |
| AD68-3 只读发现 | D1/P6 | 合法与坏包逐行发现；verify/state/render/总览毒化无影响；文件字节不变 |
| AD68-4 实际归属与消费 | D1/P7 | 真正同名同编号不同目录；两种排列；两个教授的 plan/finalize；不可变模板 wrapper 实际传递 scope |
| R68-4 原生调用、AD68-3 已安装入口、AD68-4 原生转发、AD68-1 | R1 | 两个原生 owner，各持一份 pack、完整未改 choices 与 scope；正式完成和返回结果；root 消费；最多一次后置聚合 |
| R68-6 迁移归属、R68-7 validator 委派保留 | 实现范围 | 不新增迁移；不改变 validator 路由；不复制其他议题的运行矩阵 |

P1–P7 名称及组成测试的唯一清单在 `tests/test_issue68_stage5_local_state.py`。七个外层证明只各运行一次；内部重用现有实测入口。其他回归不重复这些组成测试。R1 不证明邮件正文、validator、人性化、网页查询、写锁或迁移；缺核验时固定停止，不增加模型调用。

## 固定执行步骤

工作目录：固定 SHA 的干净 producer。可代入变量只有 `PRODUCER_ROOT`、其完整 `PRODUCER_SHA`、指定固定 fixture 的 `FIXTURE_ROOT`、提供现有 `EVAL_PORT` 的 `EVAL_DIRENV_ROOT`、新的 producer 外部证据目录 `OUTPUT_DIR`。不把用户配置、日志和真实业务数据提交到仓库。

```bash
uv run --no-project .apm/skills/professor-contact/tests/runtime/run_issue68_stage5_routing_r11.py \
  --execution-kind acceptance --case PC68-D1 \
  --producer-root "$PRODUCER_ROOT" --producer-sha "$PRODUCER_SHA" \
  --output-dir "$D1_OUTPUT_DIR"

uv run --no-project .apm/skills/professor-contact/tests/runtime/run_issue68_stage5_routing_r11.py \
  --execution-kind acceptance --case PC68-R1 \
  --producer-root "$PRODUCER_ROOT" --producer-sha "$PRODUCER_SHA" \
  --fixture-root "$FIXTURE_ROOT" \
  --fixture-sha cd5ee15b29773e4daedd28a2f5c3ecdcfc74bd04 \
  --eval-direnv-root "$EVAL_DIRENV_ROOT" --output-dir "$R1_OUTPUT_DIR"
```

正式批准前只使用 `--execution-kind preflight`，保留该性质，不能当作当前正式验收执行。`uv` 缓存目录可以设在临时目录；不改变业务输入、运行配置或断言。

只排查受影响宿主时，可在 `preflight` 的 R1 命令增加 `--preflight-host codex|opencode`。该入口只能形成局部宿主记录，整个 R1 固定为 `NOT_TESTED / partial_preflight_only`，不能生成两宿主通过；正式 acceptance 禁止此参数。外部服务故障没有新增排查价值时停止，不借局部步骤重复请求该宿主。

D1 在验证七项发现集合且开始 unittest 前写 `CASE_STARTED`；只接受 7 项普通执行，零 skip、expected failure、unexpected success。真实断言失败为 `FAIL_PRODUCT`；发现集合或执行不完整为 `INVALID_TEST_EXECUTION`。输出 `provenance.json`、`case-started.json`、`unittest.txt`、`final-verdict.json`。

R1 在新建两个独立 consumer 中按完整 SHA 执行受支持的 `apm install ... --target codex|opencode --trust-transitive-mcp`。保留命令、安装输出、退出码、锁文件、配置前后副本；禁止手改安装产物。producer 脚本只准备合成用户业务数据：A、B 各一合法本地包及原始结果，缺核验以实际安装的 plan 预检查，C 为坏包；scope 从 A/B 本地包导出；choices 含原样哨兵和无关行；保存所有初始文件哈希。

根提示固定在 `tests/runtime/prompts/issue68-stage5-root.txt`，不告诉模型发现结果、教授数或原生参数格式。只运行第五阶段，在现有核验前提停止，所有返回结果保持 JSON 的教授目录、status、reason_code。

Codex：`build_issue68_codex_request.py` 构建固定 `gpt-5.6-luna`、low、workspace-write、两个子线程、900 秒请求；通过现有 `/eval` 发送一次，既不启动也不重启服务。trust 仅用受支持内联表；固定 `--cd` 到新 consumer。原始响应经固定 fixture 的 `parse_codex_eval_evidence.py` 解析，形式 ownership 只来自 root 的 `spawnAgent` sender/receiver 关系，身份诊断不创设或否定关系。

OpenCode：固定 fixture `start_opencode_test_fixture_macos.sh` 准备一次性 HOME/XDG/TMPDIR；以白名单环境及 `cwd=consumer` 执行 `debug skill`、`debug agent professor-contact-email-generator`、唯一一次 `run --format json --model opencode/big-pickle`，最长 900 秒。退出后固定停止 fixture 并存退出码，清理失败不能判通过。正式前提和事件经 fixture 的 `parse_opencode_evidence.py` 解析。

每个宿主安装、样例预检查、配置、能力解析完成后，在唯一请求前写 `CASE_STARTED`。无 retry；不改变提示、模型、断言或业务数据找成功结果。安装和其他 bootstrap 子步骤上限分别为 240、180 秒；运行超时只终止本轮所属进程。脚本收到取消也保存判定。开始前、结束后再次检查 producer 和固定 fixture 的 SHA 与干净状态。

## 证据与唯一判定

证据来源和字段语义固定在 `tests/runtime/issue68-runtime-evidence-contract.json`，链接到带 SHA 的上游源码。Codex 使用 `rawResponseItem/completed` 的 user message 内容、正式 wait 的 `agentsStates` 返回结果、`commandExecution` 开始/完成事件及同一 generation 内严格递增 `runtime_seq`。OpenCode 使用 Task 的 `callID`、`state.input`、前台 completed 输出 `task_result`、`time.end`，root Bash 的实际输入/输出及开始时间。完整 JSON 内容按字段解析，XML 按对象解析；不以关键词次数判定。

每个 formal child/Task 的业务对象必须含唯一自己的 `email_pack`，完整 `choices` 与 `choices_scope` 必须等于样例原值。D1/P7 负责真实 runner 消费 scope；R1 负责原生边界转发，不能宣称 OpenCode root 流能观察不存在的 child Bash 事件。若观察到 owner plan，就同时检查其实际 choices 文件和 scope 文件。

root 的 discovery 必须实际返回 A/B 合法、C 错误。初始 plan 必须实测为缺核验，带结果 plan 必须实测为 `needs_refresh` 且退出码为 2；后者只证明硬门禁，不要求代理跳过正式初始步骤或返回同一原因码。两个 owner 的真实机器结果必须带原目录、未完成状态 `needs_input` 或 `needs_refresh` 及非空原因；不预设核验交互的原因枚举。root 最终按教授目录原样消费子代理实际返回的状态和原因。目录改写、错误成功、结果冲突或主代理改写为 `FAIL_PRODUCT`；没有支持的结果观察才为 `BLOCKED_OBSERVABILITY`。聚合至多一次，若存在则真实命令开始时间必须晚于两个完成结果的返回；Codex owner 不能自行聚合。

可独立重新解析已保留的证据：

```bash
uv run --no-project .apm/skills/professor-contact/tests/runtime/verify_issue68_stage5_routing.py \
  --host codex --manifest "$R1_OUTPUT_DIR/codex/fixture-manifest.json" \
  --events "$R1_OUTPUT_DIR/codex/codex-response.json" \
  --shared-verdict "$R1_OUTPUT_DIR/codex/codex-adapter.json" --output "$CODEX_VERDICT"

uv run --no-project .apm/skills/professor-contact/tests/runtime/verify_issue68_stage5_routing.py \
  --host opencode --manifest "$R1_OUTPUT_DIR/opencode/fixture-manifest.json" \
  --events "$R1_OUTPUT_DIR/opencode/opencode-run.ndjson" \
  --shared-verdict "$R1_OUTPUT_DIR/opencode/opencode-fixture-verdict.json" --output "$OPENCODE_VERDICT"
```

| 条件 | 唯一终态及停止前证据 |
| --- | --- |
| 未完成 bootstrap | `CASE_NOT_STARTED`，保留已产生安装/预检查输出与原因；不要求未来运行证据 |
| 有效执行违反 choices、scope、owner 集合、前台约定或聚合顺序 | `FAIL_PRODUCT`，保留对应正式字段与反例 |
| generation、顺序、JSON、来源或执行记录损坏，清理失败 | `INVALID_EVIDENCE` 或 `INVALID_TEST_EXECUTION`，不归因产品 |
| 外部 provider、服务、运行器阻断 | `BLOCKED_DEPENDENCY` |
| 正式观察面未暴露必需字段 | `BLOCKED_OBSERVABILITY`；不猜字段、不重采样 |
| 两个有效宿主均证明负责的全部事实 | `PASS` |

合并宿主判定按有效产品失败、无效、观察阻断、依赖阻断、未开始、两者通过的固定优先级；各宿主原始判定保留。`FAIL_PRODUCT` 对应测试规则的 `FAIL`，两个 `BLOCKED_*` 对应 `BLOCKED`，不另造通过通道。

## 步骤验证与复验条件

可执行性依据：固定 fixture、受支持安装入口、官方命令文档及固定版本源码；隔离依据：干净新 consumer、固定 SHA、一次性 OpenCode 环境、现有 eval、不改用户服务。观察依据见字段约定；真实安装和当前宿主观察假设须在本次步骤验证中核对，未知或失败不能填“已支持”。

反例和判定通道固定测试：`uv run --no-project -m unittest discover -s .apm/skills/professor-contact/tests -p test_issue68_runtime_recipe.py`。有效完整样例通过；修改 child 的原始 choices/scope 或提前聚合必须为产品失败；删除时间字段为观察阻断，打乱事件顺序为无效证据。合成样例只证明判定程序能拒绝反例，不能证明当前宿主已经委派。

复验依赖：本地包、choices 归属、状态提交、总览实现及 D1 组成测试变化命中对应 P 项；安装、agent、root 提示、模型、scope、fixture、事件来源或解析程序变化命中 R1。仅 SHA 或记录文字变化不自动使无关既有通过失效。正式第三关口没有旧结果时执行当前版本，所有尝试保留。

当前结论：`Gate 1 status: NEEDS_MODIFICATION`（完整后继冻结尚待发布）；`Gate 2 status: NEEDS_MODIFICATION`；`Gate review completeness: PARTIAL`（第十版计划批准和真实宿主步骤验证未完成）。`Test Engineer Gate 2: NEEDS_MODIFICATION`。完成后由审核者核对唯一版本、每项证明负责者、最小执行、步骤、观察、反例、无重复业务调用、判定和取代关系，发布单一完整权威记录；不能只凭本次代码修复升级为通过。
