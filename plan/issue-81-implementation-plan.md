# 第 81 号议题：送信前核验缓存格式及无进展停止——实施计划

## 1. 版本、权威来源和状态

- 议题：[professor-contact #81](https://github.com/ScholarWorkflow/professor-contact/issues/81)。
- Requirement revision：2026-10-14 创建的议题正文（读取时 `updated_at=2026-10-14T07:37:41Z`）；范围和非目标以该正文为准。
- Plan revision：`issue-81-plan-r2-2026-10-14`，本文件是唯一有效的实施计划。
- Target repository revision：`3f66656c4e82c9f0235b6dd0937ae5b2333c48f9`（2026-10-14 的 `main`，也是议题的核查基线）。
- 上游仓库版本：不涉及上游代码修改；不改变 `professor-research` 的联系方式证据格式。
- Codex 核对来源：[官方 Codex 仓库及说明](https://github.com/openai/codex)、[现有 CLI 参考链接](https://developers.openai.com/codex/cli/reference)（读取时转至通用开发者命令页）；当前问题不涉及 Codex 命令、原生委派、安装方式或工具参数。核对范围仅限这些未变更的调用边界，业务缓存的 JSON 格式以本仓库契约及 runner 为依据，不从 Codex 文档推导。
- 项目约束：[Project Consensus](https://app.notion.com/p/rekidunois/Project-Consensus-3d60101a85f3815a8c43f271f2b4d91d)、[Plan Reviewer Rule](https://app.notion.com/p/rekidunois/Plan-Reviewer-Rule-3e80101a85f3817a94cbc6eca1a76a5c)、[Test Engineer Rule](https://app.notion.com/p/rekidunois/Test-Engineer-Rule-3d80101a85f380d8a8f5ce528141e253)。
- Proposed review status: pending。**没有取得 Plan conclusion: APPROVED 前，不实施核心修复**；本文件不自行宣称任何审核或测试通过。
- 正式测试设计单独保存在 [issue-81-test-plan.md](issue-81-test-plan.md)，审核、补充执行步骤和测试结果归测试规则管理。

## 2. 需求、已知事实及边界

### 正式需求

R1. 让同一教授的 `_contact_verify.json` 写入者与消费者使用相同的源文件路径、修改时间格式与核验时间格式；代理不得靠猜测 `path:mtime` 和 `ISO-8601 UTC` 的具体写法。

R2. 核验失败必须能指出相关字段与原因，区分格式无法消费、当前记录指纹不匹配及超过 30 天。**指纹不匹配只表明缓存记录与当前文件元数据不同，不能据此证明文件内容一定被实际改动**；是否曾由真实修改、路径别名或旧写入错误引起，不做无证据归因。

R3. 对相同输入、同一未消除的核验失败，完成修复尝试后若没有进展，停止重复核验并返回阻塞结果，不进入邮件生成阶段。

保留：30 天有效期、源变更触发重核、联系方式证据新鲜度与冲突门禁、失败时停止写盘、教授级缓存共享和定向 `--email-id` 范围、已存在的结果状态及邮件 validator 轮次。非目标：缓存整体重构、哈希迁移、补造新的判断服务、全工作流回归、认证与上游行为修改。

议题已经声明：**没有本次用户机器的真实缓存、文件状态和运行结果**。本计划只解决确认的格式不一致，不宣称已经找出某次实际卡住的根因。

### 决定所依据的当前事实

| 决定 | 目标版本证据 |
| --- | --- |
| 源路径须由生产者给出，不能按固定文件名拼接 | `contact_state.py:8326-8340` 的 `load_header_sources()` 返回实际 `info_path` 和从 `find_boshu_analysis()` 取得的 `boshu_path`，前者可能不存在，后者不必位于程序根的固定名字。 |
| 指纹格式须与当前读取者一致 | `contact_state.py:8811-8880` 的 `verify_state()` 用 `f"{p}:{int(Path(p).stat().st_mtime)}"` 比较两个字段；字符串逐字相等。 |
| 核验时间采用确定的输出格式即可，不必扩大解析器 | 同处 `datetime.strptime(verified_at, "%Y-%m-%dT%H:%M:%SZ")`；`contact_state.py:139-140` 已有 `now_utc()` 生成这种 UTC 时间。 |
| 初始核验和最终落盘均必须使用同一硬门禁 | `contact_state.py:9360+` 的 `cmd_stage5_plan()` 给出 `verify` 与 `needs_recheck_professors`；`cmd_stage5_finalize()` 在写盘前调用相同 `verify_state()`；顶层 `status: ok` 不表示 `verify: ok`。 |
| 不设无条件重试 | `.apm/agents/professor-contact-email-generator.agent.md` 的“Execution summary”第 2、4 步要求重写缓存后重跑初始计划，但没有同输入重复失败的停止规则。 |
| 可保留当前测试样例入口 | `tests/test_contact_state.py` 的 `write_issue59_verify()` 已按整数秒和 `Z` 格式构造有效缓存；`tests/test_contact_evidence_ladder.py` 已有联系方式证据门禁测试。 |

以上行号和文件均以本节的目标提交为准，实施时以函数职责定位，**不把行号或测试辅助函数视为新的产品接口**。

### 与 Codex 文档的关系

本议题没有指定 `codex exec`、`spawn_agent` 参数、模型、事件字段或委派并发要求，因此未发现和所查 Codex 官方文档冲突的需求或测试条目。格式问题发生在生产者的 JSON 缓存及本地 Python 校验器。修复同时更新 Codex、OpenCode 共同消费的代理业务指令；不得借机改动两端的原生路由或用新的 Codex 调用约定补偿产品问题。

## 3. 核心方案（固定责任和接口）

### 3.1 单一规范化来源：`contact_state.py`

在当前 runner 内整理一个**纯确定性**的“当前源文件指纹”计算入口，既用于 `verify_state()` 的比较，也用于 `stage5-plan` 返回写入提示；不能复制两份略有差异的格式化算法。

- 源路径取自此次 `stage5-plan` 采用的 `load_header_sources(program_root)`。字符串形式按该函数返回值原样使用，不自行 `resolve()`、改变大小写、改相对路径或由教授姓名反推路径。
- 有效源的值等于 `f"{p}:{int(Path(p).stat().st_mtime)}"`：文件最后修改时刻的**整数 Unix 秒**，不含小数位、其他单位或时区后缀。
- 写缓存的 `verified_at` 使用已有 `now_utc()` 的格式 `%Y-%m-%dT%H:%M:%SZ`；例如 `2026-10-14T07:20:00Z`。在**本次事实核验完成后**取当前 UTC 时间，不预先写入，不把“修正字符串”冒充新核验。
- 初始 `stage5-plan` 不带 `--result` 和 `--choices` 的返回对象中**只读增加**按教授名索引的 `verify_write_hints`；教授项含 `source_fingerprints.info_json`、`source_fingerprints.boshu_analysis` 两项当前规范值，以及 `verified_at_format: "%Y-%m-%dT%H:%M:%SZ"`。已有 `verify`、`jobs` 等字段保持不变。任一源路径缺失或 `stat()` 无法取得有效修改时间时，该教授提示值为 `null`，不可写缓存；已存在缓存的此类源故障按 `missing_source` 拒绝，不得把 `:missing` 视为可匹配的有效指纹。无缓存时保留原有 `missing` 优先顺序。
- 写入者只从本次实际 plan 的提示抄取两项字符串，完成 Step 2.5 的实际核验后生成 `verified_at` 并一次写入完整教授级缓存。源在这段时间改变时，下一次 plan 的指纹比较会拒绝旧值，要求核验新源后再写，不允许直接替换指纹让旧结论“过关”。

初始 plan 的新增返回结构固定为：

```json
{
  "verify_write_hints": {
    "<教授名>": {
      "source_fingerprints": {
        "info_json": "<实际源路径>:<整数 Unix 秒>",
        "boshu_analysis": "<实际源路径>:<整数 Unix 秒>"
      },
      "verified_at_format": "%Y-%m-%dT%H:%M:%SZ"
    }
  },
  "verify_diagnostics": {
    "<教授名>": {
      "reason": "<原有 reason 或 null>",
      "failed_field": "<第一个失败字段或 null>",
      "diagnostic_kind": "<分类或 null>"
    }
  }
}
```

`verify_write_hints` 按本次被选教授输出；源不可用时用该教授名对应的 `null`，不输出半份指纹。`verify_diagnostics` 也按被选教授输出，已有 `ok` 项的三个值均为 `null`。这是拟新增的响应字段，实施完成前不得作为现有能力使用。

**选择理由**：读取者和写入提示共用同一计算入口，避免在代理文档中维护第二份路径算法。现实替代方向是仅在 `stage5-legacy-contract.md` 给出 `int(st_mtime)` 和时间示例，让代理直接读取文件状态。该方向虽少改 runner，却仍需代理自行重建 `find_boshu_analysis()` 的路径选择，继续存在写入与比较脱节的风险，故不采用。另一种扩充 ISO 时间解析器的方案也可行，但没有解决指纹路径与重复核验问题，本次保留现有严格格式。

### 3.2 可观察诊断：保留旧原因，增加字段位置

`verify_state()` 的既有 `ok`、`reason`、`path`、`data` 语义不变，针对本议题受影响的失败**附加** `failed_field` 和 `diagnostic_kind`。初始 `stage5-plan` 在不影响原有 `verify` / `needs_recheck_professors` 的前提下增加 `verify_diagnostics`，按当前教授名映射这两项及原始 `reason`。不返回完整缓存内容，不要求新报告文件。

| 情况 | 既有 `reason` | `failed_field` | `diagnostic_kind` |
| --- | --- | --- | --- |
| 指纹非规范的“当前路径:整数秒”，包括浮点时间或其他路径表示 | `stale_fingerprint` | `source_fingerprints.info_json` 或 `source_fingerprints.boshu_analysis` | `format_incompatible` |
| 记录的路径等于当前规范路径、秒数为合法整数，但当前整数秒不相等 | `stale_fingerprint` | 上述不匹配的具体字段 | `recorded_mtime_mismatch` |
| 时间字符串无法按既有严格格式解析 | `bad_timestamp` | `verified_at` | `format_incompatible` |
| 时间可解析，但相对当前 UTC 超过 30 天 | `expired` | `verified_at` | `age_expired` |
| 已有缓存但某个必需源不存在或其修改时间不可读取 | `missing_source` | 首个不可用源对应的 `source_fingerprints.info_json` 或 `source_fingerprints.boshu_analysis` | `source_unavailable` |

比较时按照现有校验顺序返回**第一项失败**；不能把本次未检查的字段声明为通过。没有实际源文件时沿用 `missing_source`（无缓存先报原有 `missing`）；文件在路径判断与取修改时间之间消失或 `stat()` 失败时，同样拒绝为 `missing_source`，避免旧的 `:missing` 字符串碰巧被当作有效指纹；邮箱证据冲突、邮箱值缺失和缓存项目缺失等其他旧原因保持原有优先级与语义。已有调用方只读取旧字段也必须继续正常工作。

当 `recorded_mtime_mismatch` 出现，只报告“记录与当前值不一致”，不对修改内容或原因作无依据判断；如果要真正判别文件内容变化，需额外历史证据，而此议题禁止哈希迁移。

### 3.3 代理在同一输入下无进展时停止

修改 `.apm/agents/professor-contact-email-generator.agent.md` 的业务步骤，同时对 `docs/stage5-legacy-contract.md` Step 2.5 作准确说明；不修改 Codex / OpenCode 路由规则。

1. 首次只调用不带 `--result`、`--choices` 的初始 `stage5-plan`，按**被选教授**的 `verify`、`verify_diagnostics` 和 `verify_write_hints` 判断下一步；顶层 `status: ok` 不能代替核验通过。
2. 对需要 Step 2.5 重核的教授，按既有在册、批次、联系方式证据、用户输入等业务步骤重新核对全部必需项目。**不能只把旧缓存的 `verified_at` 或指纹改成当前值**，因为旧事实可能已过期或源文件已变。
3. 完成真实核验后，以同一教授的完整缓存写入、同一 `email_pack` 和可选 `email_id` 重跑初始 plan。读取返回的 `verify`，仅在 `verify: ok` 后进入模型结果、用户选择、finalize、邮件校验。
4. 在同一次教授调用中，记录已经处理过的失败标识：`(教授目录, reason, failed_field, info_json 当前规范指纹或 null, boshu_analysis 当前规范指纹或 null)`；缺失源的 `null` 是失败标识的一部分，**绝不可写进缓存充当有效指纹**。完整重核后若相同标识再次出现，立即停止该教授，返回现有合法终态（源文件/证据不可用用 `needs_refresh`，缺用户确认用 `needs_input`）及该 `reason`、字段、简短阻塞说明。不能再次写相同输入的缓存，也不能继续网页核验、生成模型结果或提交邮件。若标识变化，按新失败的既有修复方式处理；本轮再次遇到已处理的标识也必须停止，防止来回震荡。**`missing_source` 或不可读取的源无法在 Stage 5 内补齐时，无须做注定失败的完整重核，首次 plan 即停止并返回 `needs_refresh`，不得空转。**
5. `contact_evidence_snapshot_stale|missing` 等原本明确要求 Stage 4 刷新邮件包的 `needs_refresh`，照旧直接交回 Stage 4；不以 Step 2.5 重写作为替代。 `contact_evidence_verify_conflict` 不得静默覆盖邮箱，要按已有显式裁决步骤处理。finalize 若拒绝，同样返回初始 plan 获取原因并服从上述停止规则，不开启第二套无界重试。
6. 只返回符合该代理现有“最终单条完整 JSON”协议的结果；保留当前 `status`、`reason_code` 含义，并在错误说明中携带确切字段及最新原因。不得把 `needs_recheck` 描述为 Stage 5 成功。

重复失败的停止仅作用于**当前教授的本轮 Stage 5**，既不清除别人的缓存，也不禁止以后源、邮件包或用户提供的新证据变化后重新执行。

## 4. 影响、安全条件及现实反例

- `intended_change`：新增从现有 runner 输出的规范指纹提示和细分失败字段；缓存时间格式的写入说明与消费者一致；不可读取的源一律不可产生合法指纹；代理不再对不变失败无界重复 Step 2.5。
- `preserved_behavior`：所有已有合法缓存直接命中；30 天 TTL 与当前严格时间解析、真实源变化后的拒绝、邮箱证据优先与升级失效、Stage 4 快照刷新、同教授复用、多封邮件及定向范围、初始 plan 与 finalize 同一门禁、邮件 validator 最多两轮保持不变。
- `approved_behavior_change`：仅议题 R1–R3 授权的写入格式确定化、诊断补充、无进展停止；源 `stat()` 失败不再允许历史 `:missing` 字符串碰巧通过，保留 fail-closed 原则；不另引入产品要求。
- `prohibited_side_effect`：篡改旧核验事实时间以越过 TTL、把未知变化当作“格式小错”直接放行、改写收件人证据、让上游证据变化绕过 Stage 4、未核验即写邮件、跨教授误报或重写、增加新命令/专用验证服务、以 Codex 外部命令取代原生委派。
- 兼容与迁移：既有可用缓存无须迁移；已写坏的缓存由现有 Step 2.5 重新核验后按新格式覆盖。新增 JSON 键是只读增量；旧返回键和值仍受支持。没有后台迁移、版本升级或额外持久化状态。

**不变量**：只有两份当前源文件指纹、`verified_at` 和现有联系方式门禁都有效，才可能得到 `verify: ok`；有 `needs_recheck` 不能开始创作或 finalize；无进展只能阻塞，不得降低核验要求。

代表性反例及处置：

- `verified_at` 为 `2026-10-14T07:20:00+00:00` 或带小数秒：仍按旧解析器给 `bad_timestamp`，诊断指向 `verified_at`；完成真实重核后用 `Z` 的秒级格式写新缓存。
- 指纹为浮点秒或指向同一文件的别名路径：报对应字段的 `format_incompatible`；不能只凭别名判断旧证据仍新鲜。
- 旧缓存记录的路径正确，但源文件 `mtime` 确实改变：`recorded_mtime_mismatch`，必须重新核验；不能套用旧 verdict。
- 有效缓存的 `verified_at` 超过 30 天：仍报 `expired`，不能用当前时间直接续期。
- 核验过程中源文件又变：复查应保持失败，不能因代理曾写入成功而跳过下一轮初始计划。
- 已有缓存但其中一份源在初始 plan 前被移走：初始 plan 返回 `missing_source`、准确源字段和 `null` 写入提示；Stage 5 无法修补源时直接阻塞，不进行无信息的重试。
- 同一教授连续两轮得到相同失败标识：在原子邮件写入前结束该教授；其余教授及原有已提交邮件状态不受影响。
- 缓存已有用户核验邮箱，但上游证据给出不同地址：保留原冲突裁决，不因本次格式修复覆盖权威邮箱。

## 5. 修改位置、先后顺序和交接

**第 0 步：审核**。提交本计划到关联 PR。依 Plan Reviewer Rule 对 P1–P4 审核，获得明确的 `Plan conclusion: APPROVED` 以后才开展产品修改；Plan owner 不能自行给出 PASS。

**第 1 步：runner**。在 `.apm/skills/professor-contact/scripts/contact_state.py` 内统一当前源指纹计算供 `verify_state()` 和初始 `cmd_stage5_plan()` 使用，新增第 3.1 节的只读提示、第 3.2 节的附加诊断。不要扩大 `verified_at` 接受格式或修改其他结果门禁。现有 `cmd_stage5_finalize()` 必须继续使用同一 `verify_state()`。

**第 2 步：生产者指令**。更新 `.apm/skills/professor-contact/docs/stage5-legacy-contract.md` Step 2.5 的格式说明、JSON 示例与真实重核前提；更新 `.apm/agents/professor-contact-email-generator.agent.md` 以读取 plan 提示并实施第 3.3 节的停止规则。必要时在 `SKILL.md` §5.9 只补一条对新细则的指向，不复制另一份计算办法。保留双运行时路由和现有最终 JSON 协议。

**第 3 步：测试代码与正式测试计划**。在生产者仓库的既有 `tests/` 中补充只覆盖 R1–R3 的回归检查；唯一测试计划为 `plan/issue-81-test-plan.md`，由本地测试工程师按获批内容补齐可运行命令、隔离配置、输出与外部故障重试停止条件。不得在 `skills-test-fixtures` 复制产品代码；不要求全仓回归或额外平台。

**第 4 步：执行与复审**。依 Test Engineer Rule 的第一关确认清单、第二关确认具体步骤，获批准后在独立 `/tmp` 运行目录执行；需要 Codex 实际运行时只使用已安装干净消费者和现有评估服务，遵循当前有效配置，不直接在 shell 中运行 `codex`。保存实际版本、逐项业务结果和必要日志；未观察到结果记无法判断或未执行，不写成通过。测试结束后按对应合并审核规则另审该 PR，不能因为本计划存在就自动合并。

**后续所有实现、测试代码和计划修订都提交到本 PR 的同一分支**，不直接提交 `main`，不提前关闭议题。只有该 PR 最终合并时，关联的 `Closes #81` 才触发关闭。

## 6. 尚未证实的事项与审核边界

- 不知道用户机器上是否确实存在坏缓存；这不是方案的必要前提，真实故障归因不在本次目标内。
- 仅有 `path:mtime` 无法区分实际文件内容被改动、时间被触碰或历史缓存值写错；本次按既有元数据契约做安全拒绝，不保证识别更细原因。
- `verify_write_hints` 和 `verify_diagnostics` 是本次提议的新增只读输出，提交前尚无实现与执行结果；属于实施顺序前置条件，不得当作已存在事实。
- 相对 r1 本次补充的是缺失源的确定行为、状态键中的 `null`、只读输出的 JSON 结构及无法取 `stat()` 时的保守拒绝；未增加必测业务目标或修改两端代理路由。
- 如实现发现上游路径选择或现有代理结果消费有影响本方案的真实新事实，先暂停对应修改并按 Plan Reviewer Rule 重开受影响决定；未受影响部分继续保留。

**交接标记：实施前待正式计划审核；测试关口与合并关口均未批准。**
