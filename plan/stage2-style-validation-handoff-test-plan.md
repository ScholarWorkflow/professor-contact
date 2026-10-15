# 第 2 阶段文字校验与修订交接——唯一测试计划

## 1. 版本、依据与状态

- **需求版本**：2026-10-15 确认的第 2 阶段文字校验交接缺陷修复目标；以本拉取请求及已批准实施计划第 2.1 节为准。
- **实施计划**：`stage2-style-validation-handoff-r1-2026-10-15`，见 [同目录实施计划](stage2-style-validation-handoff-implementation-plan.md)；[2026-10-15 实施计划审核](https://github.com/ScholarWorkflow/professor-contact/pull/86#issuecomment-6191759713)已给出 `Plan conclusion: APPROVED`。
- **测试计划版本**：`stage2-style-validation-handoff-test-r9-2026-10-16`；本文件是本次修复唯一正式测试计划。
- **仓库及设计基线**：`ScholarWorkflow/professor-contact`，`main@2a8601facb9f3bec96da6ac22c79586ca79560d7`；首次制定计划时的拉取请求提交为 `b7dd74837bfc5ed8618aca669fcf7de5623628d7`；本轮修订前基线为 PR head `d680e613e7a21e3b263df76a193aa867943eef3e`。测试准备提交为 `6b279e0d432b69d9d8511bafecf09fa3b01fa869`；首轮被测产品提交为 `a1cc974`，首次错误分类修复提交为 `45cf751`；后续修正提交为 `3d68602`，最终 8 项通过的产品提交为 `cb445f9`。
- **依据**：[测试工程师规则](https://app.notion.com/p/3d80101a85f380d8a8f5ce528141e253)、[项目共识](https://app.notion.com/p/3d60101a85f3815a8c43f271f2b4d91d)、已批准实施计划第 2～4 节；校验器原始交接格式见 `.apm/agents/professor-contact-style-validator.agent.md`。
- **状态**：C 项独立重复引文测试仍按验收决定移除；现有用户笔记保护用例增加了正文与笔记重句，并用数字字符串行号指向笔记行；再次发现引用标题行与另一叙事行重句可能误判后，同一用例也覆盖了该引用位置。针对定位文字换行误拒绝的审核意见，修正了实际行到叙事块的映射，并在同一 C 用例增加续行命中可修订的断言；未新增测试选择器。A～E 编号及验收范围未变。未受影响的第一关清单结论继续复用。测试计划 r9 已于 PR 评论 [#6197756604](https://github.com/ScholarWorkflow/professor-contact/pull/86#issuecomment-6197756604) 通过第二关。2026-10-16 首轮正式执行后，A～D 指定的 8 个用例中 7 项通过、1 项暴露目标不匹配错误分类；修正提交 `45cf751` 后只重跑该项并通过。只读完成核对随后发现字符串行号未用于消歧、且命中用户笔记或固定引用标题时可能误判可修订；同一 C 用例强化后，按原 8 个选择器在每次修正后重跑并通过。对定位换行意见修正提交 `58dd78d`，再次按原 8 个选择器全量重跑并通过。E 文档语义核对通过。测试日志和 E 核对记录位于 `/private/tmp/pc86-stage2-style-handoff.HdrM5V/`、`/private/tmp/pc86-stage2-style-handoff.rDJEmx/`、`/private/tmp/pc86-stage2-style-followup.2VcGvl/` 与 `/private/tmp/pc86-stage2-multiline-final.tyHynX/`。第三关执行已完成；本状态不表示拉取请求获准合并。

## 2. 本轮唯一必测清单

本清单以已确认业务目标及直接改变的成功、失败、兼容行为为上限。各编号中的分支只覆盖已明确规定的行为，不要求排列组合或额外扩大测试。

| 编号 | 业务目标 | 输入或场景 | 预期结果 | 检查方式 |
| --- | --- | --- | --- | --- |
| A | 原始校验报告直接接收，正确形成首次验收 | 用已由第 2 阶段生成的合成教授 `套磁候选输入.json` 与当前受管 `套磁候选分析.md`；分别提交符合校验器协议的 `result="ok", files[]`，其中唯一目标文件为该分析文件、`artifact="analysis"`，结论为 `pass` 或带轻微问题的 `pass_with_minor`。原文不含调用方自造的 `results[]/rounds/direction_id`。 | `stage2-record-validation` 不再因格式不一致返回 `invalid_validation_json`；由程序按输入包确定规范方向并记第 1 轮；两种结论均进入已接受的 `pass` 终态，轻微问题原文仍保存，不生成修订任务。 | 复用本仓库 `test_contact_state.py` 的合成输入与 `run_cli`，断言入口返回值及解析后的 `validator` 记录；轻微问题按原问题对象的 `rule/severity/location/quote/suggestion` 字段及对应关系检查完整保留，不以建议文字子串或序列化 JSON 的关键词出现作为通过条件。 |
| B | 首轮阻断进入一次定向修订，第二轮正确结束 | 当前受管分析稿含两个合成方向；校验器原始 `fail` 报告带有一条真实落在其中一个方向的 `narrative.positioning` 或 `narrative.gap_notes` 的逐字引文及位置。按 `stage2-record-validation → stage2-refine-plan → stage2-refine-finalize → stage2-record-validation` 推进；第二轮分别采用有效的通过报告和仍有阻断的失败报告。 | 第一轮产生 `needs_correction`，只为被指出方向生成修订任务；修订仅写受许可叙事，第一轮次数得到保留，修订稿在第二轮前不能算通过。第二轮通过后记已接受终态；第二轮失败后记 `fail_after_2_rounds` 并停止，不生成第三轮任务，不把失败写成通过。 | 同一组第 2 阶段生产程序入口的合成场景断言：任务方向、受管正文与输入包的叙事变化、校验轮次、预检接受状态及第二轮终态。 |
| C | 错误／陈旧报告不造成误归属或误写 | 在 A/B 的有效合成状态上分别使用代表性的本次已规定拒绝输入：调用方自造的 `results[]/rounds`；目标文件不是当前教授受管分析稿或当前正文已发生变化；阻断问题落在用户笔记、引用等不可修订区域。对已有记录的修订请求，还使用过期的正文或已变化的输入包。 | 非正式格式不被接受；无法核实当前正文或修订范围时明确拒绝，不猜测方向、不生成越界修订、不覆盖人工修改或已接受的事实，也不写出虚假的通过状态。返回状态的具体允许值按下文第 2.1 节区分入口；各类别只取足以判定这一要求的代表样例。 | 用既有程序入口检查第 2.1 节规定的拒绝状态与原因、零错误修订任务，以及 `套磁候选输入.json` 与 `套磁候选分析.md` 的受保护内容；不以某个错误状态字面值替代业务拒绝结果。 |
| D | 保留直接相关的历史接受与数据边界 | 用既有合法的 `validator.results[direction_id].result=pass/skipped` 记录，以及 B 的有效修订；分别以受支持的 `--facts`、`--professor-dir` 来源进行相关修订路径检查。 | 历史已验收记录仍可被第 2 阶段预检接受，无强制迁移；两种证据来源仍可用，输入指纹检查继续生效；修订不会改动论文事实、缺口与新近性信息、用户原文、其他教授内容或第 3～5 阶段正式输入与状态。受管正文有人工冲突时沿用原有保护。 | 仅使用第 3 节列出的相关测试和 B 的前后状态比较，按字段检查上述直接相关保留项；第 3～5 阶段未被修改的接口以本拉取请求的产品改动范围核对，不额外执行后续阶段。 |
| E | 两种正式运行环境的调用说明同步 | 对照已实施的 `packages/professor-contact-codex/.apm/agents/professor-contact-analyzer.agent.md`、`packages/professor-contact-opencode/.apm/agents/professor-contact-analyzer.agent.md` 的第 6.5 步以及 `.apm/skills/professor-contact/SKILL.md`。 | 两种环境都明确写成“原样保存校验报告 → 首轮记录 → 有需要才修订 → 重新校验 → 第二轮记录 → 停止”；不要求代理改写报告或自行编造轮次、方向；分别保留原生委派与等待方式，校验器仍只报告不改稿。 | 人工通读三份说明的对应段落，按其实际含义核对原样交接、修订条件、重新校验及停止条件，并核对各环境已有的原生委派与等待约定；记录结论及对应段落。不以关键词、固定句式、正则表达式或词语出现顺序判定通过，不新增运行时委派认证或模型冒烟。 |

A、B 覆盖正式成功路径与两轮上限；C 只检查已确认的拒绝与保护行为；D、E 是实施计划明确要求保留或同步的直接影响。不得将本表外的理论反例、通用身份认证、全仓回归或测试平台建设作为通过条件。

### 2.1 C 项拒绝状态：准确数量与适用入口

**本次不新增任何产品返回状态（新增 0 种）。** 对现有两处仅断言 `status == "error"` 的过期输入测试，允许的拒绝状态明确为 **2 种：`error` 和 `needs_refresh`**，即在原来 1 种的基础上增加 **1 种既有状态 `needs_refresh`**。选择取决于实际拒绝原因，不能要求产品对同一次输入同时返回两种状态：

| 受检入口及场景 | 允许的 `status` | 必须检查的业务结果 |
| --- | --- | --- |
| `stage2-record-validation` 收到调用方自造的 `results[]/rounds`，不符合原始 `files[]` 协议 | 仅 `error`（`reason_code=invalid_validation_json`） | 不写入校验通过记录，不修改受管文件 |
| `stage2-record-validation` 的报告不再对应当前受管分析正文 | `error` 或 `needs_refresh`，共 2 种 | 返回明确原因，保护人工修改的正文，不写入过期通过结果 |
| `stage2-refine-plan`／`stage2-refine-finalize` 的已记录修订请求所依赖的输入包或正文已变化 | `error` 或 `needs_refresh`，共 2 种 | 返回明确原因，不生成可误用的修订任务，不覆盖已变化的包和正文 |
| `stage2-refine-finalize` 在写回受管 Markdown 时发现人工冲突（既有行为，D 项保留） | `needs_decision`（`reason_code=manual_markdown_changed`） | 等待人工决定，不覆盖文件；该状态**不加入**上面 C 项两处过期输入断言 |

任何 C 项拒绝场景返回 `ok`、返回可继续错误修订的 `needs_correction`、悄悄覆盖数据或伪造通过，均不满足预期。对问题在不可修订区等其余 C 项情况，只检查**明确阻塞及零误写**；已批准实施计划未冻结其唯一状态名称，不能擅自加一套新的状态码通过条件。`needs_decision` 属于已有的人工冲突保护，不应混入 `stage2-record-validation` 的报告失效测试；本次也不要求额外执行一遍已有的人工冲突保护测试。

## 3. 测试实现与执行交接

1. **受影响测试代码与准备修正**：现有 `.apm/skills/professor-contact/tests/test_contact_state.py` 把阶段 2 的校验报告改为原始 `result + files[] + notes`；`test_stage2_style_validation_handoff.py` 覆盖两轮终态、过期输入、不可修订区及历史接受。下列既有准备继续适用；清单内测试准备已完成，正式运行仅采用第 5 项列出的 8 个测试；本轮执行结果见第 4 节：
   - **路径（A、B）**：`stage2_preflight_direction` 的 `--target-file` 指向上游夹具创建的 `套磁目标.json`；未修改产品入口。
   - **叙事与局部修改（B）**：双方向样例中新增的无占位符叙事段使用 `refs=[]`；`test_13_stage2_validator_rewrite_round_trips_structured_narrative` 将目标方向的完整 `positioning` 列表交给 `stage2-refine-finalize`，仅修改命中段，保留其他段与 `gap_notes`。
   - **双方向夹具（B）**：`stage2_run_two_directions` 保留 `write_facts()` 返回的路径供正式入口读取，另从文件解析 JSON 对象并读取 `directions`；仍复用 B 项现有样例，不增加用例。
   - **规范方向身份（B）**：双方向样例让规范 `direction_id`（`DIR00001`、`DIR00002`）与旧 `collection_key`（`legacy-alpha`、`legacy-beta`）不同；通过现有 Stage 0／2 夹具及正式入口形成输入包，没有直接伪造已接受输入包。修订请求、任务和回写按 `direction_id` 路由，并比较另一方向及目标方向的非叙事字段。
   - **拒绝状态与受保护内容（C）**：陈旧正文与变化输入包的断言按第 2.1 节接受 `error` 或 `needs_refresh`，要求明确原因并检查没有输入包写入或错误任务；相关的 `stage2-refine-plan` 检查也排除 `reason_code=invalid_validation_json`。陈旧正文测试也检查目标文件不受管时拒绝且不改写。不可修订用户笔记用例让同一句引文同时出现在可修改定位正文和受保护笔记中，并用数字字符串行号分别指向笔记行及论文引用标题行；引用标题命中的同一句还出现在另一条可修改叙事行中，以确认不能跨行借用叙事来源。该用例也包含带换行的定位条目，并用数字字符串行号指向续行，确认可修订问题进入 `needs_correction`，且修订计划只为目标方向生成任务。在 `stage2-record-validation` 与 `stage2-refine-plan` 前后比较 `套磁候选输入.json` 的 `directions` 和 `套磁候选分析.md` 正文。记录入口必须明确拒绝笔记及引用标题命中，修订计划明确阻塞、有原因且 `jobs` 为空，不固定唯一状态名。允许顶层独立 `validator` 区域记录失败信息，不要求整个输入包逐字节相同。上述报告拒绝及修订计划检查均排除 `reason_code=invalid_validation_json`，确认样例已按原始 `files[]` 协议解析后识别场景；原始 `results[]` 格式错误仍只接受 `error/invalid_validation_json`；`needs_decision` 不加入上述两条断言。
   - **问题保存断言（A）**：轻微问题断言现在读取 JSON 中对应方向的 `issues`，逐项核对原问题对象的 `rule/severity/location/quote/suggestion` 字段及关系；不搜索序列化文本，也不判断建议措辞。
   - **调用说明检查（E）**：已移除 `test_stage2_calling_docs_keep_the_raw_report_sequence` 的词语、条件词和出现顺序断言。E 只按本节第 5 项人工语义核对；Codex `spawn_agent` 与 OpenCode 原生 `task` 的正式委派、等待要求保持不变，不增加真实工具调用、日志认证或冒烟。
   - **边界与覆盖**：仅在合成教授目录调用正式 `contact_state.py`，不通过测试夹具伪造正式方向或轮次。第 5 项列出的 8 个程序用例覆盖 A～D，E 使用同一计划中的人工核对；没有新增测试平台或业务目标。
2. **正式运行前版本确认（已完成）**：首轮被测产品提交为 `a1cc974`，测试准备提交为 `6b279e0d432b69d9d8511bafecf09fa3b01fa869`。错误分类由 `45cf751` 修复；后续在 `3d68602` 和最终产品提交 `cb445f9` 上按相同 8 个选择器重跑 A～D；E 沿用本节人工核对；没有扩大用例范围。
3. **准备顺序和配置来源**：从目标工作树仓库根目录确认 `git rev-parse --show-toplevel`；设置 `PC86_RUN_ROOT` 为 `/private/tmp` 下新建的独立目录；切换到 `.apm/skills/professor-contact/tests`。只需本地 Python 标准库和仓库内测试辅助模块，无外部服务、账户或密钥。按预检结果复用 `UV_CACHE_DIR=/private/tmp/pc81-uv-cache`，命令使用 `uv run --offline --no-project`，不联网安装依赖。
4. **有限环境预检记录（2026-10-16）**：复核结果为 `uv 0.12.22`、计划命令使用的 `uv run` Python `3.14.6`；`unittest`、`issue64_test_support`、`stage2_upstream_fixture`、`test_contact_state`、`test_stage2_style_validation_handoff` 可导入；`/private/tmp` 与 `/private/tmp/pc81-uv-cache` 可写。命令及输出记录在独立目录 `/private/tmp/pc86-preflight-20261016.eeskjs/preflight.txt`。仅检查版本、模块导入及目录写入能力，未调用必测命令、正式用例、产品入口或业务请求。默认 UV 缓存目录此前确认不可写，后续命令继续使用已检查可写的 `/private/tmp/pc81-uv-cache`。
5. **A～D 正式命令与 E 人工核对记录**：在测试资产修正完成、产品修复提交及第二关确认后，从目标工作树根目录执行以下命令。本轮实际产品／测试提交号及 `PC86_RUN_ROOT` 已记录；日志仅保存在独立 `/private/tmp` 目录；不因文档或提交号变化重跑未受影响的有效通过结果。

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
     test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_stage2_nonrepairable_user_note_does_not_create_a_correction_job \
     test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_stage2_refinement_rejects_changed_input_pack \
     test_stage2_style_validation_handoff.Stage2ValidationHandoffTests.test_stage2_preflight_accepts_legacy_pass_and_skipped_records \
     > "$PC86_RUN_ROOT/unittest.log" 2>&1; then
     cat "$PC86_RUN_ROOT/unittest.log"
   else
     PC86_EXIT_CODE=$?
     cat "$PC86_RUN_ROOT/unittest.log"
     exit "$PC86_EXIT_CODE"
   fi
   ```

   `test_contact_state.TestRunnerBasics.test_13...` 用 `--facts` 生成修订计划，用 `--professor-dir` 提交修订；其余相关用例复用同一本地夹具。`TemporaryDirectory` 为每项提供独立、用后清理的合成教授目录。

   **E 的执行方式（已完成）**：已人工通读两份第 6.5 步、主技能对应段落和校验器返回格式，确认原始报告交接、首轮修订条件、第二轮复核与终止，以及各环境的原生委派和等待要求均一致。结论为通过；实际版本和段落位置记录在 `/private/tmp/pc86-stage2-style-handoff.rDJEmx/manual-e-review.md`。该记录中的主技能支持位置应按“Stage 2 在 Codex 下的委派链与用户选择”后的“Step 6.5 — 白话校验循环”节名定位；记录已更正为相应核对版本的行号。判断依据为说明所表达的动作、条件和顺序；未运行模型或真实调用链。
6. **失败处理和结果位置**：保留 `$PC86_RUN_ROOT/unittest.log`。目标命令已启动且断言不符时记录业务失败，不因结果不满意重跑；运行时、导入或命令启动失败时记“无法判断／未执行”，先修复环境，再只补做受影响项。测试夹具在每个用例结束后清理；临时输出不入库。
7. **关口交接**：A～E 清单范围不变，第一关清单结论沿用；测试计划第二关已由 PR 评论 #6197756604 确认通过。第三关于 2026-10-16 完成：A～D 的 8 项最终均通过，E 人工核对通过。具体执行记录见下节；第三关结果不代替合并审核。

## 4. 本轮执行记录

- **产品实施**：已提交并推送，产品提交为 `a1cc974`、`45cf751`、`3d68602`、来源匹配修正 `cb445f9` 和定位换行修正 `58dd78d`。
- **A～D 程序用例**：在 `/private/tmp/pc86-stage2-style-handoff.HdrM5V/unittest.log` 的首轮运行（产品提交 `a1cc974`）中，8 项里 7 项通过，陈旧正文用例发现目标不匹配被错误分类为 `invalid_validation_json`。修正后只重跑该项，在 `/private/tmp/pc86-stage2-style-handoff.rDJEmx/unittest.log` 通过。完成核对又发现数字字符串行号未用于消歧、且可能跨 positioning 行借用重复短句判定可修订；现有 C 用例同时指向用户笔记行和含相同引文的固定论文标题行，引用标题对应的可编辑重复句位于另一条叙事行。`3d68602` 上对原 8 个选择器的先前完整重跑记录在 `/private/tmp/pc86-stage2-style-followup.2VcGvl/unittest-final.log`；来源匹配修正先运行 C 项并通过，随后在 `cb445f9` 上按原 8 个选择器重新运行，全部通过，耗时 8.334 秒，日志位于 `/private/tmp/pc86-stage2-source-final.BFsien/unittest-final.log`。定位换行修正提交 `58dd78d` 后，原 8 个选择器再次全部通过，耗时 12.150 秒；同一 C 用例确认续行上的报告可修订并只生成目标方向任务。完整日志位于 `/private/tmp/pc86-stage2-multiline-final.tyHynX/unittest-final.log`。
- **E 文档核对**：通过。核对结论、版本和段落位置记于 `/private/tmp/pc86-stage2-style-handoff.rDJEmx/manual-e-review.md`；主技能段落按章节标题定位，避免沿用错误行号。
- **环境**：复用 2026-10-16 有限预检，`uv 0.12.22`、Python `3.14.6`；正式用例使用离线缓存 `/private/tmp/pc81-uv-cache`。日志与人工记录均未入库。
- **测试资产与审核状态**：r9 未增加独立重复引文测试或测试选择器；现有用户笔记保护用例以数字字符串行号分别指向用户笔记、固定论文标题和带换行定位条目的续行，并检查明确拒绝、零误写和目标方向修订任务。第一关结论沿用，第二关已通过，第三关既有清单执行完成；定位换行修正后再次完整重跑原 8 个选择器。拉取请求仍保持草稿，未作合并决定。
