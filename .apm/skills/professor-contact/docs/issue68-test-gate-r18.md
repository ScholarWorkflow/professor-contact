# Issue #68 / PR #72 本地测试工程师实现记录 r18

记录版本：`issue68-r18-owner-business-input-2026-10-04`。

本文件是**实现记录，不是第二关口权威结论**。它记录按 Test Engineer r17（PR 评论 `5979948032`）指派完成的 `PC68-R1` 证据提取与判定实现修正、冻结条件的保持情况、回归证据，以及本地对已保存正式 raw 的实现性重判。是否重开第二关口、是否要求新的 Preflight、以及最终权威修订号由测试工程师决定。

## 1. 指派与缺陷

r16（评论 `5979892792`）把本次正式 `PC68-R1` 的 `BLOCKED_OBSERVABILITY / completed_user_payload_unobservable` 归为 `RECIPE / REVIEW_DEFECT`；r17（评论 `5979948032`）更正了处置方向：不需要先扩 fixture 或 eval-server，现有 `eval raw` 已包含判断所需的机器证据。

缺陷本体（修正前冻结的 r13/r14 判定器 `verify_issue68_stage5_routing_r13.py` 继承的基础判定器 `verify_issue68_stage5_routing.py`）：

```text
child 业务输入来源被固定为
rawResponseItem/completed -> item.type = message -> item.role = user
-> content[].type = input_text -> 明文 JSON 含 email_pack / choices / choices_scope
```

真实 Codex V2 child 入口是：

```text
rawResponseItem/completed -> item.type = agent_message
-> content[0] = input_text（只有 NEW_TASK 外壳）
-> content[1] = encrypted_content（任务正文为密文）
```

因此 `payloads[child]` 为空，判定器在业务判断之前就返回 `BLOCKED_OBSERVABILITY / completed_user_payload_unobservable`；而同一份 raw 中 owner 自己实际消费的明文业务对象就记录在它自己的 `commandExecution` 里。这同时命中两种错误：把已有可归属证据判成不可观察，以及把已存在的产品违规事实掩盖成观察阻断。

## 2. 本次修正后的唯一 owner 业务输入来源

正式 child thread 自己的 `commandExecution`（`message.method = item/completed`，`item.type = commandExecution`）命令文本中记录的明文业务对象：

```text
每个 formal child 恰好一个可归属业务对象
  -> email_pack、choices、choices_scope 交给冻结的内容条件判定
0 个          -> BLOCKED_OBSERVABILITY / owner_business_object_unobservable
多个不同对象  -> INVALID_EVIDENCE / owner_business_object_ambiguous
```

命令文本可能把对象嵌在 shell 引号里，并以 JSON 或 Python 字面量（`False`/`None`）两种形式出现；r18 从同一份文本解出受支持的形式，两种都能读取：

```text
\" 转义 -> 引号区域内容 -> 对象文本
对象文本 -> JSON 值（沿用基础判定器 json_values/objects）
        -> Python 字面量（花括号平衡区域 + ast.literal_eval）
```

明文 child user message 仍是**投递面回退**：只有在 child 完全没有可读 `commandExecution` 业务对象时才使用；投递面缺失时保留原原因码 `completed_user_payload_unobservable`。

## 3. 保持不变的冻结判定

| 冻结事实 | r18 实现 | 结果 |
| --- | --- | --- |
| 正式归属只用 adapter @16 formal topology | 沿用基础判定器 | 不变 |
| root 最终业务结果只在当前 generation / root thread / 当前 turn 的唯一 `final_answer` | 继续用 r13 selector | 不变 |
| 每个 child 恰好一份合法 `email_pack`，不重复不交换 | `unexpected_owner_pack`、`duplicate_owner_pack` | 原因码不变 |
| 每个 child 含完整、未改 `choices` | 缺字段 `choices_transport_missing`、不等 `choices_transport_changed` | 原因码不变 |
| 每个 child 含完整、未改 `choices_scope` | 缺字段 `choices_scope_transport_missing`、不等 `choices_scope_transport_changed` | 原因码不变 |
| wait 不得早于 owner 完成 | `wait_precedes_owner_completion` | 原因码不变 |
| 观察缺失 → `BLOCKED_OBSERVABILITY`；证据损坏或歧义 → `INVALID_EVIDENCE` | 沿用 | 不变 |
| 事件顺序或 generation 损坏 → `INVALID_EVIDENCE` | 沿用 | 不变 |

### 3.1 `choices_scope` 比较按解析后的映射

受支持的 `choices_scope` 值是映射 `professor_dir -> email_ids`（产品 `contact_state.py` 的 `stage5_choices_scope` 只接受对象形式；caller 也可能传等价的 `[{professor_dir, email_ids}]` 列表）。r18 因此比较解析后的映射，而不是序列化形式；`professor_dir` 字符串与 `email_id` 仍必须逐字等于 caller 的规范值，任何改写（例如 `試験` → `试验`）都是 `FAIL_PRODUCT`。

依据：`PROJECT_CONSENSUS.md`「逐次调用的输入与输出证据」规定字节完全相同只用于正式要求明确规定原样传递的情形，要求只规定数据含义相同时按解析后的字段与关系判断，不增加缩进、字段顺序要求。冻结要求是「完整、未改的 `choices_scope`」，不是某一序列化形状。若不做这层归一，`試験` 改写与形状差异会一起被判成 `choices_scope_transport_changed`，忠实转发的 child 也会被错误判失败。

### 3.2 已证明的产品失败不得被降级

按 r15 §7「任何 `FAIL_PRODUCT` 不得被改写为 blocked/invalid」，r18 先按 `sorted(children)` 逐个判定并分类，再按 `FAIL_PRODUCT` → `INVALID_EVIDENCE` → `BLOCKED_OBSERVABILITY` 取最高优先级返回；同时把基础判定器对 set 顺序的隐式依赖改为固定顺序，使 verdict 可机械复现。

## 4. 版本化资产

```text
.apm/skills/professor-contact/tests/runtime/verify_issue68_stage5_routing_r18.py
.apm/skills/professor-contact/tests/runtime/run_issue68_stage5_routing_r18.py
.apm/skills/professor-contact/tests/runtime/run_issue68_stage5_routing_r18_codex.py
.apm/skills/professor-contact/tests/runtime/issue68-runtime-evidence-contract-r18.json
.apm/skills/professor-contact/tests/test_issue68_runtime_r18.py
```

r13/r12/r11 资产未修改；r14 的服务来源与存储隔离检查由 r18 入口继续复用（`issue68_eval_service_isolation_r14.py`）。r18 契约把 runner 固定为 `run_issue68_stage5_routing_r18_codex.py`，并在 `codex` 段增加 `owner_business_input_source`、`owner_business_input_exclusions`、`owner_business_input_fallback`、`choices_scope_equivalence`、`terminal_precedence`。

## 5. 回归证据

命令（工作树 head = 本记录所在提交，Python 3.12）：

```bash
uv run --no-project --python 3.12 python -m unittest \
  discover -s .apm/skills/professor-contact/tests -p 'test_*.py' -v
```

结果：`Ran 929 tests in 184.447s`，`OK`，无失败、错误或跳过；929 = 本分支 69 个测试文件里全部 `def test_` 数量。CI 记录的 1003 项是在与最新 `main` 的合成提交上运行，包含 `main` 侧新增测试，口径不同。

`test_issue68_runtime_r18.py` 20 项全部通过，覆盖：

- 真实 `agent_message` + `input_text` NEW_TASK 外壳 + `encrypted_content` 形状下，从 child `commandExecution` 读出业务对象并判 `PASS`；
- JSON 形式与 Python 字面量形式的命令载荷都能读出；
- 对象形式与列表形式的 `choices_scope` 等价；
- `choices_scope` 目录改写 → `FAIL_PRODUCT / choices_scope_transport_changed`（不是 blocked）；
- `choices` 改写、缺 `choices`、非法 `email_pack` → 对应 `FAIL_PRODUCT` 原因码；
- 一个 child 无业务对象、另一个 child 目录被改写 → 仍判 `FAIL_PRODUCT`（不被阻断掩盖）；
- 命令面无对象 → `BLOCKED_OBSERVABILITY / owner_business_object_unobservable`；完全无明文面 → 原 `completed_user_payload_unobservable`；
- 两个不同对象 → `INVALID_EVIDENCE / owner_business_object_ambiguous`；
- wait 早于 owner 完成、owner 数量错误、事件顺序损坏、旧 turn 结果不得成为终态；
- bridge 绑定、契约字段与 Codex-only 入口唯一性。

同时复跑 r11–r14 既有模块（`test_issue68_runtime_r13.py`、`r12`、`r12_codex`、`r14`、`recipe`、`r11_bridge`、`m1`、`m2`、`stage5_local_state`、`choices_attribution`）全部 `OK`。

## 6. 对已保存正式 raw 的实现性重判

命令（不发送任何模型请求，不改动归档）：

```bash
python .apm/skills/professor-contact/tests/runtime/verify_issue68_stage5_routing_r18.py --host codex \
  --manifest   /tmp/pr72-r1-formal-f230616984/codex/fixture-manifest.json \
  --events     /tmp/pr72-r1-formal-f230616984/codex/codex-response.json \
  --shared-verdict /tmp/pr72-r1-formal-f230616984/codex/codex-adapter.json \
  --output     /tmp/pc68-r18-work/r18-rejudge-real-raw.json
```

结果：

```text
verdict     = FAIL_PRODUCT
reason_code = choices_scope_transport_changed
observed_pack = .../教授研究/Y分野/佐藤 花子/邮件输入.json
observed_scope = { ".../X分野/试验 教授": ["試験 教授::DIR00001::DIR00001_1"],
                   ".../Y分野/佐藤 花子": ["佐藤 花子::DIR00001::DIR00001_1"] }
expected_scope = { ".../X分野/試験 教授": [...], ".../Y分野/佐藤 花子": [...] }
```

逐 child 事实（同一 raw）：

| formal child | 命令数 | child 任务入口 | 读出业务对象 | `email_pack` | payload 判定 | `turn/completed` |
| --- | --- | --- | --- | --- | --- | --- |
| `01a106cd-2036…`（X） | 11 | `agent_message` + `input_text`/`encrypted_content` | 1 | `X分野/試験 教授` | `PASS` | seq 14573 |
| `01a106cd-47d0…`（Y） | 9 | 同上 | 1 | `Y分野/佐藤 花子` | `FAIL_PRODUCT / choices_scope_transport_changed` | seq 14673 |

`试验` 只出现在 Y child 线程（首个位置 seq 14430 的 `custom_tool_call`，命令载荷见 seq 14491/14585/14607），root 线程与 X child 始终是 `試験`，即改写发生在 Y owner 自己构造并实际消费的载荷里。

本次只是实现性验证：正式第三关口重判仍须在第二关口复审通过后由有权执行者按新权威记录进行。

## 7. 给测试工程师的未决事项

1. **wait / consume 观察面**：本次 raw 的 `collabAgentToolCall wait` 四项（seq 14026、14575、14581、14675）`receiverThreadIds` 为空、`agentsStates` 为空，按冻结判定该条件对两个 child 都是 `completion_or_wait_unobservable`。本次 verdict 由已证明的产品失败优先决定，不受影响；但若后续 raw 的载荷干净，这条 R1 条件仍需要可观察来源。同一 raw 中存在可按 child 归属的替代事件面：root 线程的 `subAgentActivity`（`kind=completed`，带 `agentThreadId`，X seq 14572、Y seq 14672）。是否改用该面属于第二关口决定，r18 未自行更改。
2. **是否要求新的 Preflight**：r18 只改 owner 业务输入来源，请求构建器、root final-source selector、模型、reasoning、sandbox、fixture adapter 与 eval-server revision 均未变，因此 r13 capability 与 r14 isolation 证据按各自复验依赖继续有效；owner 业务输入面本身已有同一服务实例、同一 revision 的既有 characterization（第 6 节）。是否需要为它再执行一次非验收探测由测试工程师决定。
3. **入口与归档清单**：r18 入口沿用 r14 的服务来源与隔离检查及归档项；若第二关口要把 `subAgentActivity` 或其它字段纳入正式归档，需要相应更新契约与归档清单。

## 8. 本地证据位置

| 路径 | 内容 |
| --- | --- |
| `/tmp/pc68-r18-work/full-suite.log` | 全量回归日志（Ran 929 tests, OK） |
| `/tmp/pc68-r18-work/r18-rejudge-real-raw.json` | 新判定器对已保存 raw 的输出 |
| `/tmp/pc68-r18-work/real-raw-breakdown.json` | 逐 child 事实分解 |
| `/tmp/pc68-r18-work/raw-characterization.txt` | 修正前对真实 raw 业务对象来源的 characterization |
| `/tmp/pr72-r1-formal-f230616984` | r15 正式尝试官方归档（未改动） |
