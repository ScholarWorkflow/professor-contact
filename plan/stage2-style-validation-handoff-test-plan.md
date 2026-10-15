# 第 2 阶段文字校验与修订交接——唯一测试计划

## 1. 版本、依据与状态

- **需求版本**：2026-10-15 确认的第 2 阶段文字校验交接缺陷修复目标；以本拉取请求及已批准实施计划第 2.1 节为准。
- **实施计划**：`stage2-style-validation-handoff-r1-2026-10-15`，见 [同目录实施计划](stage2-style-validation-handoff-implementation-plan.md)；[2026-10-15 实施计划审核](https://github.com/ScholarWorkflow/professor-contact/pull/86#issuecomment-6191759713)已给出 `Plan conclusion: APPROVED`。
- **测试计划版本**：`stage2-style-validation-handoff-test-r3-2026-10-15`；本文件是本次修复唯一正式测试计划。
- **仓库及设计基线**：`ScholarWorkflow/professor-contact`，`main@2a8601facb9f3bec96da6ac22c79586ca79560d7`；首次制定计划时的拉取请求提交为 `b7dd74837bfc5ed8618aca669fcf7de5623628d7`；现有测试资产已提交至 `ed46ea386e5aa24915a212d4347fcc9e5a7c510c`。本次修订仅更新测试计划；产品修复尚未提交，实际被测产品提交待实施后填写。
- **依据**：[测试工程师规则](https://app.notion.com/p/3d80101a85f380d8a8f5ce528141e253)、[项目共识](https://app.notion.com/p/3d60101a85f3815a8c43f271f2b4d91d)、已批准实施计划第 2～4 节；校验器原始交接格式见 `.apm/agents/professor-contact-style-validator.agent.md`。
- **状态**：A～E 必测目标保持不变。本轮复核发现现有测试资产仍有路径、合成叙事、方向身份及拒绝状态断言问题，修正要求见第 3 节；不得据此前的准备复审声称现有步骤已可直接通过第二关。第一、第二关待有权审核者依当前文件确认；第三关尚未执行。产品修复尚未进入 PR；不宣称测试通过、实施完成或准许合并。

## 2. 本轮唯一必测清单

本清单以已确认业务目标及直接改变的成功、失败、兼容行为为上限。各编号中的分支只覆盖已明确规定的行为，不要求排列组合或额外扩大测试。

| 编号 | 业务目标 | 输入或场景 | 预期结果 | 检查方式 |
| --- | --- | --- | --- | --- |
| A | 原始校验报告直接接收，正确形成首次验收 | 用已由第 2 阶段生成的合成教授 `套磁候选输入.json` 与当前受管 `套磁候选分析.md`；分别提交符合校验器协议的 `result="ok", files[]`，其中唯一目标文件为该分析文件、`artifact="analysis"`，结论为 `pass` 或带轻微问题的 `pass_with_minor`。原文不含调用方自造的 `results[]/rounds/direction_id`。 | `stage2-record-validation` 不再因格式不一致返回 `invalid_validation_json`；由程序按输入包确定规范方向并记第 1 轮；两种结论均进入已接受的 `pass` 终态，轻微问题原文仍保存，不生成修订任务。 | 复用本仓库 `test_contact_state.py` 的合成输入与 `run_cli`，断言入口返回值及 `套磁候选输入.json` 的 `validator` 记录。 |
| B | 首轮阻断进入一次定向修订，第二轮正确结束 | 当前受管分析稿含两个合成方向；校验器原始 `fail` 报告带有一条真实落在其中一个方向的 `narrative.positioning` 或 `narrative.gap_notes` 的逐字引文及位置。按 `stage2-record-validation → stage2-refine-plan → stage2-refine-finalize → stage2-record-validation` 推进；第二轮分别采用有效的通过报告和仍有阻断的失败报告。 | 第一轮产生 `needs_correction`，只为被指出方向生成修订任务；修订仅写受许可叙事，第一轮次数得到保留，修订稿在第二轮前不能算通过。第二轮通过后记已接受终态；第二轮失败后记 `fail_after_2_rounds` 并停止，不生成第三轮任务，不把失败写成通过。 | 同一组第 2 阶段生产程序入口的合成场景断言：任务方向、受管正文与输入包的叙事变化、校验轮次、预检接受状态及第二轮终态。 |
| C | 错误／陈旧报告不造成误归属或误写 | 在 A/B 的有效合成状态上分别使用代表性的本次已规定拒绝输入：调用方自造的 `results[]/rounds`；目标文件不是当前教授受管分析稿或当前正文已发生变化；阻断引文无法唯一归属方向；阻断问题落在用户笔记、引用等不可修订区域。对已有记录的修订请求，还使用过期的正文或已变化的输入包。 | 非正式格式不被接受；无法核实当前正文、方向或修订范围时明确拒绝，不猜测方向、不生成越界修订、不覆盖人工修改或已接受的事实，也不写出虚假的通过状态。返回状态的具体允许值按下文第 2.1 节区分入口；各类别只取足以判定这一要求的代表样例。 | 用既有程序入口检查第 2.1 节规定的拒绝状态与原因、零错误修订任务，以及 `套磁候选输入.json` 与 `套磁候选分析.md` 的受保护内容；不以某个错误状态字面值替代业务拒绝结果。 |
| D | 保留直接相关的历史接受与数据边界 | 用既有合法的 `validator.results[direction_id].result=pass/skipped` 记录，以及 B 的有效修订；分别以受支持的 `--facts`、`--professor-dir` 来源进行相关修订路径检查。 | 历史已验收记录仍可被第 2 阶段预检接受，无强制迁移；两种证据来源仍可用，输入指纹检查继续生效；修订不会改动论文事实、缺口与新近性信息、用户原文、其他教授内容或第 3～5 阶段正式输入与状态。受管正文有人工冲突时沿用原有保护。 | 复用受影响的现有第 2 阶段测试及 B 的前后状态比较，按字段检查上述直接相关保留项；第 3～5 阶段未被修改的接口以本拉取请求的产品改动范围核对，不额外执行后续阶段。 |
| E | 两种正式运行环境的调用说明同步 | 对照已实施的 `packages/professor-contact-codex/.apm/agents/professor-contact-analyzer.agent.md`、`packages/professor-contact-opencode/.apm/agents/professor-contact-analyzer.agent.md` 的第 6.5 步以及 `.apm/skills/professor-contact/SKILL.md`。 | 两种环境都明确写成“原样保存校验报告 → 首轮记录 → 有需要才修订 → 重新校验 → 第二轮记录 → 停止”；不要求代理改写报告或自行编造轮次、方向；分别保留原生委派与等待方式，校验器仍只报告不改稿。 | 直接核对三份正式安装／技能说明的对应段落、调用顺序与已有的原生委派约定；只审文本一致性，不新增逐次调用记录、运行时委派认证或模型冒烟。 |

A、B 覆盖正式成功路径与两轮上限；C 只检查已确认的拒绝与保护行为；D、E 是实施计划明确要求保留或同步的直接影响。不得将本表外的理论反例、通用身份认证、全仓回归或测试平台建设作为通过条件。

### 2.1 C 项拒绝状态：准确数量与适用入口

**本次不新增任何产品返回状态（新增 0 种）。** 对现有两处仅断言 `status == "error"` 的过期输入测试，允许的拒绝状态明确为 **2 种：`error` 和 `needs_refresh`**，即在原来 1 种的基础上增加 **1 种既有状态 `needs_refresh`**。选择取决于实际拒绝原因，不能要求产品对同一次输入同时返回两种状态：

| 受检入口及场景 | 允许的 `status` | 必须检查的业务结果 |
| --- | --- | --- |
| `stage2-record-validation` 收到调用方自造的 `results[]/rounds`，不符合原始 `files[]` 协议 | 仅 `error`（`reason_code=invalid_validation_json`） | 不写入校验通过记录，不修改受管文件 |
| `stage2-record-validation` 的报告不再对应当前受管分析正文 | `error` 或 `needs_refresh`，共 2 种 | 返回明确原因，保护人工修改的正文，不写入过期通过结果 |
| `stage2-refine-plan`／`stage2-refine-finalize` 的已记录修订请求所依赖的输入包或正文已变化 | `error` 或 `needs_refresh`，共 2 种 | 返回明确原因，不生成可误用的修订任务，不覆盖已变化的包和正文 |
| `stage2-refine-finalize` 在写回受管 Markdown 时发现人工冲突（既有行为，D 项保留） | `needs_decision`（`reason_code=manual_markdown_changed`） | 等待人工决定，不覆盖文件；该状态**不加入**上面 C 项两处过期输入断言 |

任何 C 项拒绝场景返回 `ok`、返回可继续错误修订的 `needs_correction`、悄悄覆盖数据或伪造通过，均不满足预期。对无法唯一定位引文、问题在不可修订区等其余 C 项情况，只检查**明确阻塞及零误写**；已批准实施计划未冻结其唯一状态名称，不能擅自加一套新的状态码通过条件。`needs_decision` 属于已有的人工冲突保护，不应混入 `stage2-record-validation` 的报告失效测试；本次也不要求额外执行一遍已有的人工冲突保护测试。

## 3. 测试实现与执行交接

1. **受影响测试代码与本轮待落实修正**：现有 `.apm/skills/professor-contact/tests/test_contact_state.py` 已把阶段 2 的校验报告改为原始 `result + files[] + notes`；`test_stage2_style_validation_handoff.py` 已增加两轮终态、过期输入、方向歧义、不可修订区、历史接受及调用说明的检查。**下列项目仍须由本地测试工程师在正式运行前修正既有测试资产；本轮仅修订正式计划，不宣称测试代码已修复：**
   - **路径错误（A、B）**：`stage2_preflight_direction` 的 `--target-file` 由 `套磁目標.json` 改为上游夹具实际创建的 `套磁目标.json`；不修改产品入口。
   - **合法叙事与局部修改（B）**：`stage2_run_two_directions(include_unaffected_positioning=True)` 中新增的无占位符叙事段设 `refs=[]`，保持 `refs` 与正文引用标记一致；`test_13_stage2_validator_rewrite_round_trips_structured_narrative` 交给 `stage2-refine-finalize` 的 `positioning` 必须是该方向的**完整**叙事段列表，只改变命中的目标段，其他段和 `gap_notes` 保持原样。按原有断言比较未命中段与事实字段，不增加另一套检查。
   - **规范方向身份（B）**：同一双方向合成样例至少让被修订方向的 `direction_id` 与旧 `collection_key` 具有**不同但合法**的值，并按正式 Stage 0／2 输入及已接受解析关系生成状态；不得直接伪造已接受的输入包。断言修订任务及回写使用规范 `direction_id`，另一方向不变。该改动用于发现误用旧 `collection_key` 的现有 B 项风险，不另建身份认证设施。
   - **拒绝状态（C）**：`test_stage2_report_for_stale_render_is_rejected_without_pack_write` 和 `test_stage2_refinement_rejects_changed_input_pack` 的状态断言按第 2.1 节接受 `error` 或 `needs_refresh`，同时断言有明确原因、零错误任务／越界写入；原始 `results[]` 格式错误仍只接受 `error/invalid_validation_json`。`needs_decision` 不加入上述两条断言。C 项已列明的目标文件不符，可合入现有 C 测试的代表场景核对，沿用当前入口与选择器，不新增独立测试平台或第六项业务目标。
   - **调用说明（E）**：继续静态检查现有两种环境的原生委派约定及本次第 6.5 步顺序。已有 Codex `spawn_agent`、OpenCode 原生 `task` 要求不变；不要求额外验证真实工具调用、增加日志认证或新增冒烟。
   - **边界与交付**：只在合成教授目录调用仓库正式 `contact_state.py`，不通过测试夹具自造正式方向或轮次。修订后对照 A～E 复核选择器仍能覆盖已确认目标，只有必要时更新同一份第 5 步命令。
2. **正式运行前填写版本**：产品实施完成并进入本分支后，记录产品提交号和测试提交号；确认下列选择器仍指向计划 A～E 的检查，再运行。修订前的 PR 头 `ed46ea386e5aa24915a212d4347fcc9e5a7c510c` 尚无产品修复，现有测试也有第 1 项列出的待修改处，因此这些用例尚未运行，没有可填写的产品通过版本。
3. **准备顺序和配置来源**：从目标工作树仓库根目录确认 `git rev-parse --show-toplevel`；设置 `PC86_RUN_ROOT` 为 `/private/tmp` 下新建的独立目录；切换到 `.apm/skills/professor-contact/tests`。只需本地 Python 标准库和仓库内测试辅助模块，无外部服务、账户或密钥。按预检结果复用 `UV_CACHE_DIR=/private/tmp/pc81-uv-cache`，命令使用 `uv run --offline --no-project`，不联网安装依赖。
4. **有限环境预检记录（2026-10-15）**：`uv 0.12.22`；`Python 3.14.6`；`unittest`、测试所需标准库以及 `issue64_test_support`、`stage2_upstream_fixture`、`test_contact_state` 可导入；`/private/tmp` 可写。未调用必测命令、产品入口或业务请求。默认 UV 缓存目录不可写，因此后续命令固定使用上述 `/private/tmp` 缓存目录。
5. **A～E 待执行命令**：**只在第 1 项测试资产修正、产品修复提交及第二关确认后**，从目标工作树根目录执行以下命令。执行工程师记录实际产品／测试提交号及 `PC86_RUN_ROOT`，输出仅保存在独立 `/private/tmp` 目录；不因文档或提交号变化重跑未受影响的有效通过结果。

   ```sh
   PC86_REPO="$(git rev-parse --show-toplevel)"
   PC86_TEST_DIR="$PC86_REPO/.apm/skills/professor-contact/tests"
   PC86_RUN_ROOT="$(mktemp -d /private/tmp/pc86-stage2-style-handoff.XXXXXX)"
   cd "$PC86_TEST_DIR"
   if UV_CACHE_DIR=/private/tmp/pc81-uv-cache uv run --offline --no-project python -m unittest -v \
     test_contact_state.TestRunnerBasics.test_11_stage2_validator_is_persisted_separately \
     test_contact_state.TestRunnerBasics.test_11a_stage2_validator_pass_with_minor_is_accepted \
     test_contact_state.TestRunnerBasics.test_13_stage2_validator_rewrite_round_trips_structured_narrative \
     test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_stage2_second_blocking_round_is_terminal \
     test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_stage2_report_for_stale_render_is_rejected_without_pack_write \
     test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_stage2_ambiguous_quote_does_not_create_a_correction_job \
     test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_stage2_nonrepairable_user_note_does_not_create_a_correction_job \
     test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_stage2_refinement_rejects_changed_input_pack \
     test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_stage2_preflight_accepts_legacy_pass_and_skipped_records \
     test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_stage2_calling_docs_keep_the_raw_report_sequence \
     > "$PC86_RUN_ROOT/unittest.log" 2>&1; then
     cat "$PC86_RUN_ROOT/unittest.log"
   else
     PC86_EXIT_CODE=$?
     cat "$PC86_RUN_ROOT/unittest.log"
     exit "$PC86_EXIT_CODE"
   fi
   ```

   `test_contact_state.TestRunnerBasics.test_13...` exercises `--facts` for planning and `--professor-dir` for finalization; the other affected cases use the same local fixture. The helper's `TemporaryDirectory` gives each case a disposable synthetic professor directory. No real library, browser, account, or user data is read.
6. **失败处理和结果位置**：保留 `$PC86_RUN_ROOT/unittest.log`。目标命令已启动且断言不符时记录业务失败，不因结果不满意重跑；运行时、导入或命令启动失败时记“无法判断／未执行”，先修复环境，再只补做受影响项。测试夹具在每个用例结束后清理；临时输出不入库。
7. **关口交接**：A～E 清单范围不变；旧准备复审不能替代第 1 项所列修正的落地核验。第一关（清单范围）与第二关（步骤可执行性）仍待有权审核者在本修订版上确认；第三关未开始。测试工程师先修正现有测试代码并核对选择器，执行工程师随后使用确认的同一入口记录产品版本及逐项结果。

## 4. 当前未完成项

- **产品实施**：仍待 `contact_state.py`、两种 analyzer 安装投影与主技能说明的修改。
- **测试资产修正**：第 3 节第 1 项列出的现有测试夹具、输入与断言待本地测试工程师落实；未运行证明其有效。
- **正式执行**：A～E 均未执行；没有新增的通过结果。
- **独立审核**：第一、第二关审核仍待有权审核者确认；本轮未开展独立子代理计划复核，不将旧准备审核或本文修订写成关口批准。
