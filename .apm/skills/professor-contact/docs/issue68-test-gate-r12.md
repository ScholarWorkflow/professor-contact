# 第 68 号议题：第二关测试方案后继记录

记录版本：`issue-68-gate2-r12-2026-10-04`。

本文件只定义第二关测试证明、证据来源、固定判定和第三关推进条件。它不把合成回归、自测或历史运行升级为第三关通过，也不授权启动、停止或重启现有服务。

## 当前有效输入

| 项目 | 当前来源 |
| --- | --- |
| Requirement revision | `2026-09-29 user requirement — per-professor state at every stage`，加 2026-10-01 独立合并澄清 |
| Frozen Acceptance Contract | `issue-68-gate1-r2-2026-10-02`，保留 `PASS + COMPLETE` |
| Canonical Plan | `issue-68-plan-r11-2026-10-02`，批准记录 `pr72-plan-r11-review-r2-2026-10-02` |
| 产品行为基准 | `d49f587753aed5721b2fe7ddff465e96c0621212`（产品行为基准不变，本轮产品代码零改动）；本轮只改测试资产、请求配置和测试说明 |
| 目标仓库修订 | 由本记录的 gate2-r12 权威发布版（issue #68 评论）冻结；正式执行时 `$PRODUCER_SHA` 取该冻结修订，`$PRODUCER_ROOT` 在其上检出干净 |
| Base revision | `2ed4da800a6e2ff557d7b37a36db810ccddd5c7e` |
| Fixture | `RekiDunois/skills-test-fixtures@cd5ee15b29773e4daedd28a2f5c3ecdcfc74bd04` |
| Codex 默认配置 | 项目共识 `PROJECT_CONSENSUS.md`（更新时间 2026-10-04 14:41）：默认 Codex profile 为 `--model gpt-6-luna --config 'model_reasoning_effort="low"'`；该共识修订取代 `issue-68-gate2-r11-2026-10-04` 所引用的旧共识默认 `gpt-5.6-luna` |
| 正式入口 | `.apm/skills/professor-contact/tests/runtime/run_issue68_stage5_routing_r12_codex.py`（2026-10-04 范围调整：`PC68-R1` 只执行 Codex 宿主，无多宿主合并判定） |
| 证据约定 | `.apm/skills/professor-contact/tests/runtime/issue68-runtime-evidence-contract-r12.json`，revision=`issue-68-runtime-evidence-r12-2026-10-04` |
| Merge Gate cases | `PC68-D1`、`PC68-R1` |
| 本轮来源 | `pr72-test-review-r2-2026-10-04` |

本记录取代 `issue-68-gate2-r11-2026-10-04` 中受本轮复审影响的 `PC68-R1` 最终业务结果来源、判定程序、相关回归、运行请求配置和执行前观察约定。`PC68-D1/P1–P7` 的既有通过继续复用，不重新枚举未受影响步骤。

模型来源唯一链条：`gpt-5.6-luna` → `gpt-6-luna` 的唯一来源是上表所引共识修订（`PROJECT_CONSENSUS.md`，更新时间 2026-10-04 14:41）。该修订取代下列旧表述在 `PC68-R1` 上的效力：`docs/issue68-test-gate.md` 第 97 行附近"构建固定 `gpt-5.6-luna`"条款，以及 r11 构建器 `build_issue68_codex_request.py` 及其回归 `test_issue68_runtime_recipe.py` 中的 `gpt-5.6-luna` 断言。上述 r11 资产作为历史一代保留在树中，不删除、不再作为 `PC68-R1` 的请求配置来源；`PC68-R1` 的唯一请求配置来源是 r12 构建器 `build_issue68_codex_request_r12.py` 加本表所引共识修订。

## 重开范围

本轮只有两类变化命中 `PC68-R1`：

1. `RECIPE / REVIEW_DEFECT`：原判定器把根线程全部历史文本合并后再检查最终结果，可把历史引用当成最终业务结果，产生错误拒绝。
2. 配置来源变化：本轮复审结束后，项目共识中的默认 Codex 模型更新为 `gpt-6-luna`，因此固定请求必须跟随当前共识。该变化只命中 `PC68-R1` 的运行配置，不重开确定性证明。
3. 入口接线修正（本轮审核缺陷 D1 的修复）：基础运行器在 `codex_host`/`opencode_host` 内以进程内函数直接调用 `build_request`、`verify_codex`、`verify_opencode`，不经过子进程，argv 改写到不了这三处。第十二版入口因此把基础运行器模块的这三个属性重绑到 r12 构建器与 r12 判定器实现，管线中唯一走子进程的判定依赖（Codex 共享解析器）继续改写为设施根线程历史包装器。接线由回归 `test_bridge_pins_base_runner_bindings_to_r12_implementations` 与 `test_base_runner_pipeline_uses_r12_final_source_and_consensus_model` 固定。

没有确认产品实现缺陷，没有重开正式计划，也不修改产品要求。

## 2026-10-04 测试范围调整（权威记录 `issue-68-gate2-r12-2026-10-04` 后继）

当前运行测试 `PC68-R1` 只保留 Codex 宿主，不再以多宿主运行或合并判定作为验收前提；`PC68-D1/P1–P7` 的范围和既有通过复用不变。由此产生的执行约束：

1. 正式入口唯一：`run_issue68_stage5_routing_r12_codex.py`。最终判定即 Codex 宿主判定（`PASS` / `FAIL_PRODUCT` / `INVALID_EVIDENCE` / `INVALID_TEST_*` / `BLOCKED_OBSERVABILITY` / `BLOCKED_DEPENDENCY`），原样落 `final-verdict.json`，不做任何多宿主合并。
2. 旧 `PC68-R1` 通用运行命令（含 `run_issue68_stage5_routing.py` 与 `run_issue68_stage5_routing_r12.py` 的直接调用）停止作为执行指令，仅作历史与管线实现保留；不得把仅允许执行前检查的 `--preflight-host codex` 当作正式验收。
3. 正式运行恢复后先执行一次最小能力检查；失败即按预设出口停止，不发起正式用例、不临场重试、不换服务、不换模型、不改断言。能力检查是独立前置步骤，不算正式验收。
4. 接线由回归 `tests/test_issue68_runtime_r12_codex.py` 固定：入口只执行 Codex（不触 OpenCode 路径、不调用 `combine`）、构建器/判定器/契约/设施绑定正确（`gpt-6-luna`、`cd5ee15b29773e4daedd28a2f5c3ecdcfc74bd04`）、判定直通不合并、归档清单完整、producer 与 fixture 修订运行前后校验干净。

## `PC68-R1` 最终业务结果来源

### Codex

根线程最终业务结果只允许来自本次运行同一根线程、同一 `runtime_generation` 的：

```text
output.root_thread_read
  -> request == thread/read(threadId=<root>, includeTurns=true)
  -> result.thread.id == <root>
  -> turns 按原顺序
  -> 最后一个 turn
  -> 该 turn 必须恰好有一个 AgentMessage phase=final_answer
  -> 只消费该 AgentMessage.text
```

`phase=commentary`、`phase` 缺失或未知、较早 turn、实时事件中的历史 assistant 消息、嵌套诊断都不能进入最终业务结果数组。

如果 `root_thread_read`、归属信息或最后一个 turn 中可识别的 `final_answer` 缺失，判 `BLOCKED_OBSERVABILITY`；字段损坏、归属不匹配或最后一个 turn 有多个 `final_answer`，判 `INVALID_EVIDENCE`。不得依据模型文字含义猜哪个消息是最终消息，也不得退回较早 turn 的 `final_answer`。

### OpenCode

固定入口继续使用 `opencode run --format json`。该命令只把根 session 的已完成 text part 输出到 JSON 流；每个可用 text part 必须具备 `id`、`sessionID`、`messageID`、`text` 和 `time.end`。

根线程最终业务结果固定为：**两个前台 owner task 都完成之后，事件流中最后一个已完成根 text 事件的 `text`**。所有更早的 text 事件都是历史/过程文本，不得与最终结果合并。

没有 owner 完成后的最终 text 时判 `BLOCKED_OBSERVABILITY`；结构字段损坏判 `INVALID_EVIDENCE`。

### 判定器共同约束

第十二版入口只把一个已经由宿主解析器固定的最终根消息传给既有业务判定器。历史根文本不会进入 `runtime_checks()`。

在唯一最终来源内部：

- 每位教授必须有一条可归属结果；真正缺结果按既有 `BLOCKED_OBSERVABILITY / root_consumed_result_unobservable` 处理。
- 同一教授在最终来源中出现互相矛盾的 `status/reason_code`，判 `FAIL_PRODUCT / root_consumed_results_conflict`。
- 最终来源改写 owner 返回结果，判 `FAIL_PRODUCT / root_changed_owner_result`。
- 最终来源损坏，判 `INVALID_EVIDENCE / root_final_result_malformed`。

## M1 修复确认条件

两宿主都必须覆盖以下反例，不允许用单一“合法通过”样例代替：

1. 前置历史消息包含与某教授冲突的伪造行，随后唯一最终消息原样包含两位教授真实结果：`PASS`。
2. 历史消息包含正确结果，唯一最终消息含矛盾或改写结果：`FAIL_PRODUCT`。
3. 唯一最终消息自身存在同目录矛盾：`FAIL_PRODUCT / root_consumed_results_conflict`。
4. 真正没有可识别最终消息：`BLOCKED_OBSERVABILITY`。
5. 唯一最终消息损坏：`INVALID_EVIDENCE`。
6. Codex 最后一个 turn 只有 `phase` 未知的 assistant 消息：`BLOCKED_OBSERVABILITY`，不得猜测。
7. Codex 较早 turn 有合法 `final_answer`、最后一个 turn 没有可识别终态：`BLOCKED_OBSERVABILITY`，不得退回旧终态。

这些合成回归只证明判定程序不会按已知反例误判，不构成真实宿主第三关通过。判定程序第 34–54 行的 `INVALID_EVIDENCE` 分支由 `test_codex_thread_read_contract_violations_are_invalid`（`root_thread_read` 损坏、归属不匹配、请求形状不匹配、错误结果损坏、result/thread/turns/turn/item 损坏、最后 turn 多个 `final_answer` 的 `root_final_message_ambiguous`）与 `test_opencode_final_source_contract_violations_are_invalid`（根会话不唯一、text part 字段损坏）逐一覆盖；`root_thread_read.error` 非空的阻断路径由 `test_codex_thread_read_error_blocks_without_fabricating_final_message` 固定。

## M2 保留

第十一版已经修复的“来源完整性先于业务内容”规则继续有效：

- 完整、可归属的 owner payload 缺 `choices` 或 `choices_scope`：`FAIL_PRODUCT`。
- 完整、可归属的 owner 完成结果没有业务结果字段：`FAIL_PRODUCT`。
- 真正没有来源：`BLOCKED_OBSERVABILITY`。
- 归属歧义或证据不可解析：`INVALID_EVIDENCE`。

本轮 M1 不改变这些分类。

## 执行前观察条件

当前已知服务探测结果显示 HTTP 200、运行完成、退出码 0，但响应 `output` 没有 `root_thread_read`。该结果只证明当前实例缺少 `PC68-R1` 所需观察面，不证明产品失败。证据指针：PR #72 评论 5977201809（https://github.com/ScholarWorkflow/professor-contact/pull/72#issuecomment-5977201809）；本机归档目录 `/tmp/professor-contact-68-r1-probe-r11-FNFYw08h/`，其中 `root-thread-read-probe-response.json` 显示 `passed=true` 且 `output.root_thread_read` 不存在，`probe-verdict.json` 判 `CAPABILITY_ABSENT / STOP_BEFORE_FORMAL_PC68_R1`（单次执行，未重试）。

正式 `PC68-R1` 继续暂停。恢复后只允许先做一次最小能力检查，并保存：

- 实际运行实例的直接构建来源；
- 与本次运行对应的根线程编号和 `runtime_generation`；
- `root_thread_read` 请求、返回和同运行归属；
- `AgentMessage phase=final_answer` 可观察性；
- 本证明依赖的隔离证据；
- OpenCode 旧依赖故障的恢复事实。

最小能力检查失败时按预设出口停止，不发起正式用例、不临场重试、不换服务、不换模型、不改断言。

## 固定执行入口（Codex 专用）

能力检查满足后，正式运行由本地执行代理调用唯一入口。入口固定 `PC68-R1`、`execution_kind=acceptance`、宿主为 `codex`，不接受 `--case`、`--execution-kind`、`--preflight-host` 参数。

### 执行步骤

1. **执行前检查（引导阶段，入口自动执行）**：入口唯一性（`sys.argv[0]` 必须解析为本入口，否则 `entrypoint_uniqueness_violated`）；r12 证据契约校验（revision、fixture SHA、runner 指向本入口、`manual_patch=no`）；设施 fixture SHA 必须等于 `cd5ee15b29773e4daedd28a2f5c3ecdcfc74bd04`；`$PRODUCER_ROOT` 必须检出 `$PRODUCER_SHA` 且工作树干净；输出目录必须不存在或为空且在 producer 之外。
2. **最小能力检查（独立前置步骤，不算正式验收）**：正式运行前执行一次最小能力检查并保存"执行前观察条件"一节所列六项证据；检查失败即按预设出口停止，不发起正式用例、不临场重试、不换服务、不换模型、不改断言。能力检查的任何结果都不写 `final-verdict.json` 判定。
3. **正式运行（唯一一次 Codex 请求）**：执行下方命令。入口把冻结管线进程内重绑到 r12 资产（共识请求构建器 `build_issue68_codex_request_r12.py`、最终来源判定器 `verify_issue68_stage5_routing_r12.verify_codex`、设施根线程历史解析器包装器），只调用 Codex 宿主一次，请求失败不重试、不换服务、不换模型、不改断言。
4. **归档**：输出目录按下方归档清单留档；`$PRODUCER_ROOT` 与 `$FIXTURE_ROOT` 在运行结束后再次校验干净，任何漂移判 `INVALID_TEST_EXECUTION / revision_or_execution_changed`。

### 正式运行命令

```bash
uv run --no-project python \
  .apm/skills/professor-contact/tests/runtime/run_issue68_stage5_routing_r12_codex.py \
  --producer-root "$PRODUCER_ROOT" \
  --producer-sha "$PRODUCER_SHA" \
  --fixture-root "$FIXTURE_ROOT" \
  --fixture-sha cd5ee15b29773e4daedd28a2f5c3ecdcfc74bd04 \
  --eval-direnv-root "$EVAL_DIRENV_ROOT" \
  --output-dir "$R1_OUTPUT_DIR"
```

`$PRODUCER_SHA` 必须等于"当前有效输入"表中由权威发布版（issue #68 评论）冻结的目标仓库修订；`$PRODUCER_ROOT`、`$FIXTURE_ROOT`、`$EVAL_DIRENV_ROOT`、`$R1_OUTPUT_DIR` 沿用 r11 记录的代入约定。所有尝试都必须保留。不得把步骤验证、合成回归、旧阻断结果或能力检查当作正式宿主通过。

### 历史命令（停止作为执行指令，仅历史）

下列通用运行命令自 2026-10-04 范围调整起停止作为执行指令，仅作历史记录与管线实现保留；不得再用它发起 `PC68-R1` 正式运行，也不得把 `--preflight-host codex` 的部分运行当作验收：

```bash
uv run --no-project python \
  .apm/skills/professor-contact/tests/runtime/run_issue68_stage5_routing_r12.py \
  --case PC68-R1 --execution-kind acceptance ...   # 仅历史，停止使用
```

### 归档清单（输出目录，与 r12 证据契约对齐）

| 文件 | 产生者 |
| --- | --- |
| `provenance.json`（producer/fixture 修订、`execution_kind=acceptance`、`host=codex`、`single_request_no_retry=yes`） | 入口引导阶段 |
| `codex/install.json`、`codex/install.*.txt`（apm install 命令与输出） | 冻结管线 `install_host` |
| `codex/apm.lock.yaml`、`codex/installed-entrypoint.json`（consumer 安装与唯一入口脚本） | 冻结管线 `install_host` |
| `codex/fixture-manifest.json`、`codex/canonical-choices.json`、`codex/expected-scope.json`、`codex/root-prompt.txt`、`codex/owner-*` 业务输入 | 冻结管线 `prepare` |
| `codex/config.toml.before`、`codex/config.toml.after`（consumer 配置前后快照） | 冻结管线 `archive_config` |
| `codex/codex-request.json`（r12 共识构建器产物：`gpt-6-luna` + `model_reasoning_effort="low"`） | 冻结管线 `codex_host` |
| `codex/case-started.json`、`codex/codex-response.json`（唯一一次正式请求的原始响应） | 冻结管线 `codex_host` |
| `codex/codex-adapter.json`、`codex/shared-parser.*.txt`（设施根线程历史包装器解析产物） | 冻结管线共享解析器 |
| `codex-verdict.json`（Codex 宿主判定） | 入口 |
| `final-verdict.json`（与 `codex-verdict.json` 逐字段一致；无多宿主合并） | 入口 |

## 第三关处置

| 用例 | 当前决定 |
| --- | --- |
| `PC68-D1/P1–P7` | `REUSE_PRIOR_PASS`。产品行为及确定性证明依赖未被本轮测试修复命中 |
| 旧 `PC68-R1` Codex | 保留既有 `BLOCKED_OBSERVABILITY`；旧证据没有可补造的 `root_thread_read` |
| 旧 `PC68-R1` OpenCode | 保留既有 `BLOCKED_DEPENDENCY`；没有新恢复事实 |
| 当前 `PC68-R1` | `EXECUTE_CURRENT`（只执行 Codex 宿主，经"固定执行入口（Codex 专用）"一节的唯一入口），但在执行前观察条件满足之前不得启动正式验收 |

完整旧证据只有在自身已经包含修正后所需的最终消息归属事实时才能 `REJUDGE_PRIOR_EVIDENCE`；缺失字段不得补写。

## 当前关口结论

| 关口 | 结论 | 完整性 |
| --- | --- | --- |
| Gate 1 | `PASS` | `COMPLETE`，未重开 |
| Gate 2 | `NEEDS_MODIFICATION` | `PARTIAL`：M1 判定器与回归已修正；当前正式服务观察能力、实际服务构建来源和隔离依据仍未满足 |
| Gate 3 | `NOT_READY` | `PARTIAL`：确定性通过可复用；当前必需运行未执行 |

`Merge conclusion: NOT_READY`。

恢复所需观察能力由有权维护当前实例的人处理。测试工程师只负责固定证据要求和判定；本地执行代理只能在前置条件满足后按本记录执行。