# 第 2 阶段文字校验与修订交接——唯一测试计划

## 1. 版本、依据与状态

- **需求版本**：2026-10-15 确认的第 2 阶段文字校验交接缺陷修复目标；以本拉取请求及已批准实施计划第 2.1 节为准。
- **实施计划**：`stage2-style-validation-handoff-r1-2026-10-15`，见 [同目录实施计划](stage2-style-validation-handoff-implementation-plan.md)；[2026-10-15 实施计划审核](https://github.com/ScholarWorkflow/professor-contact/pull/86#issuecomment-6191759713)已给出 `Plan conclusion: APPROVED`。
- **测试计划版本**：`stage2-style-validation-handoff-test-r2-2026-10-15`；本文件是本次修复唯一正式测试计划。
- **仓库及设计基线**：`ScholarWorkflow/professor-contact`，`main@2a8601facb9f3bec96da6ac22c79586ca79560d7`；制定计划时的拉取请求提交为 `b7dd74837bfc5ed8618aca669fcf7de5623628d7`。测试资产准备基于 PR 提交 `2df992d731e06538618453382db3395cb9fe1f91`；该提交仍不含产品修复，实际被测产品提交待实施后填写。
- **依据**：[测试工程师规则](https://app.notion.com/p/3d80101a85f380d8a8f5ce528141e253)、[项目共识](https://app.notion.com/p/3d60101a85f3815a8c43f271f2b4d91d)、已批准实施计划第 2～4 节；校验器原始交接格式见 `.apm/agents/professor-contact-style-validator.agent.md`。
- **状态**：测试准备符合性复审完成，A～E 对应测试资产与步骤覆盖完整；首次审核发现的缺口已修订并复查。第一关（必测清单）及第二关（可执行步骤）仍待有权审核者审核；第三关（实际结果）未开始。产品修复尚未进入 PR，因此本轮未运行测试。本计划不宣称测试通过、实施完成或准许合并。

## 2. 本轮唯一必测清单

本清单以已确认业务目标及直接改变的成功、失败、兼容行为为上限。各编号中的分支只覆盖已明确规定的行为，不要求排列组合或额外扩大测试。

| 编号 | 业务目标 | 输入或场景 | 预期结果 | 检查方式 |
| --- | --- | --- | --- | --- |
| A | 原始校验报告直接接收，正确形成首次验收 | 用已由第 2 阶段生成的合成教授 `套磁候选输入.json` 与当前受管 `套磁候选分析.md`；分别提交符合校验器协议的 `result="ok", files[]`，其中唯一目标文件为该分析文件、`artifact="analysis"`，结论为 `pass` 或带轻微问题的 `pass_with_minor`。原文不含调用方自造的 `results[]/rounds/direction_id`。 | `stage2-record-validation` 不再因格式不一致返回 `invalid_validation_json`；由程序按输入包确定规范方向并记第 1 轮；两种结论均进入已接受的 `pass` 终态，轻微问题原文仍保存，不生成修订任务。 | 复用本仓库 `test_contact_state.py` 的合成输入与 `run_cli`，断言入口返回值及 `套磁候选输入.json` 的 `validator` 记录。 |
| B | 首轮阻断进入一次定向修订，第二轮正确结束 | 当前受管分析稿含两个合成方向；校验器原始 `fail` 报告带有一条真实落在其中一个方向的 `narrative.positioning` 或 `narrative.gap_notes` 的逐字引文及位置。按 `stage2-record-validation → stage2-refine-plan → stage2-refine-finalize → stage2-record-validation` 推进；第二轮分别采用有效的通过报告和仍有阻断的失败报告。 | 第一轮产生 `needs_correction`，只为被指出方向生成修订任务；修订仅写受许可叙事，第一轮次数得到保留，修订稿在第二轮前不能算通过。第二轮通过后记已接受终态；第二轮失败后记 `fail_after_2_rounds` 并停止，不生成第三轮任务，不把失败写成通过。 | 同一组第 2 阶段生产程序入口的合成场景断言：任务方向、受管正文与输入包的叙事变化、校验轮次、预检接受状态及第二轮终态。 |
| C | 错误／陈旧报告不造成误归属或误写 | 在 A/B 的有效合成状态上分别使用代表性的本次已规定拒绝输入：调用方自造的 `results[]/rounds`；目标文件不是当前教授受管分析稿或当前正文已发生变化；阻断引文无法唯一归属方向；阻断问题落在用户笔记、引用等不可修订区域。对已有记录的修订请求，还使用过期的正文或已变化的输入包。 | 非正式格式不被接受；无法核实当前正文、方向或修订范围时明确报错或报告阻塞，不猜测方向、不生成越界修订、不覆盖人工修改或已接受的事实，也不写出虚假的通过状态。各类别只取足以判定这一要求的代表样例。 | 用既有程序入口断言错误／阻塞结果；比较受影响的 `套磁候选输入.json` 与 `套磁候选分析.md` 的受保护内容和是否产生错误修订任务。 |
| D | 保留直接相关的历史接受与数据边界 | 用既有合法的 `validator.results[direction_id].result=pass/skipped` 记录，以及 B 的有效修订；分别以受支持的 `--facts`、`--professor-dir` 来源进行相关修订路径检查。 | 历史已验收记录仍可被第 2 阶段预检接受，无强制迁移；两种证据来源仍可用，输入指纹检查继续生效；修订不会改动论文事实、缺口与新近性信息、用户原文、其他教授内容或第 3～5 阶段正式输入与状态。受管正文有人工冲突时沿用原有保护。 | 复用受影响的现有第 2 阶段测试及 B 的前后状态比较，按字段检查上述直接相关保留项；第 3～5 阶段未被修改的接口以本拉取请求的产品改动范围核对，不额外执行后续阶段。 |
| E | 两种正式运行环境的调用说明同步 | 对照已实施的 `packages/professor-contact-codex/.apm/agents/professor-contact-analyzer.agent.md`、`packages/professor-contact-opencode/.apm/agents/professor-contact-analyzer.agent.md` 的第 6.5 步以及 `.apm/skills/professor-contact/SKILL.md`。 | 两种环境都明确写成“原样保存校验报告 → 首轮记录 → 有需要才修订 → 重新校验 → 第二轮记录 → 停止”；不要求代理改写报告或自行编造轮次、方向；分别保留原生委派与等待方式，校验器仍只报告不改稿。 | 直接核对三份正式安装／技能说明的对应段落与执行入口；此项目标是调用说明同步，不附加完整运行时委派或模型冒烟认证。 |

A、B 覆盖正式成功路径与两轮上限；C 只检查已确认的拒绝与保护行为；D、E 是实施计划明确要求保留或同步的直接影响。不得将本表外的理论反例、通用身份认证、全仓回归或测试平台建设作为通过条件。

## 3. 测试实现与执行交接

1. **受影响测试代码**：已在 `.apm/skills/professor-contact/tests/test_contact_state.py` 更新原先手工构造 `results[]` 的阶段 2 测试，使用校验器原始 `result + files[] + notes` 对象；新增 `test_stage2_style_validation_handoff.py` 覆盖两轮终态、第二轮前后预检接受状态、过期正文和输入包保护、方向歧义（检查两个方向均未被误记为通过）、不可修订区域、历史 `pass/skipped` 接受及调用说明。修订回归逐字段比较被指出方向的缺口注释和未命中叙事块。三份调用说明依次检查原样交接、首次记录、仅在 `needs_correction` 时修订、修订后通过对应运行环境原生委派重新校验、第二次记录和停止；Codex 段核对原生子代理名称与等待，OpenCode 段核对 `task` 指定校验器与等待。夹具只使用合成教授与仓库真实 `contact_state.py` 命令入口，不补造方向或轮次。
2. **正式运行前填写版本**：产品实施完成并进入本分支后，记录产品提交号和测试提交号；确认下列选择器仍指向计划 A～E 的检查，再运行。当前 PR 头 `2df992d731e06538618453382db3395cb9fe1f91` 尚无产品修复，因此这些用例尚未运行，也没有可填写的产品通过版本。
3. **准备顺序和配置来源**：从目标工作树仓库根目录确认 `git rev-parse --show-toplevel`；设置 `PC86_RUN_ROOT` 为 `/private/tmp` 下新建的独立目录；切换到 `.apm/skills/professor-contact/tests`。只需本地 Python 标准库和仓库内测试辅助模块，无外部服务、账户或密钥。按预检结果复用 `UV_CACHE_DIR=/private/tmp/pc81-uv-cache`，命令使用 `uv run --offline --no-project`，不联网安装依赖。
4. **有限环境预检记录（2026-10-15）**：`uv 0.12.22`；`Python 3.14.6`；`unittest`、测试所需标准库以及 `issue64_test_support`、`stage2_upstream_fixture`、`test_contact_state` 可导入；`/private/tmp` 可写。未调用必测命令、产品入口或业务请求。默认 UV 缓存目录不可写，因此后续命令固定使用上述 `/private/tmp` 缓存目录。
5. **A～E 执行命令**：在目标工作树根目录执行以下命令。`PC86_RUN_ROOT` 与实际产品提交号由执行工程师填写；测试输出仅保存在独立 `/private/tmp` 目录。

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
7. **关口交接**：测试准备符合性复审已确认 A～E 覆盖完整；第一关（A～E 范围）与第二关（步骤和测试实现可执行性）仍待有权审核者完成；第三关未开始。后续本地执行工程师仅按上述选择器运行，并填写实际产品提交号及逐项结果。

## 4. 当前未完成项

- **产品实施**：仍待 `contact_state.py`、两种 analyzer 安装投影与主技能说明的修改。
- **正式执行**：A～E 均未执行；没有新增的通过结果。
- **独立审核**：测试准备符合性复审已确认覆盖完整；第一、第二关审核仍待有权审核者完成，本文件不将准备工作表述为关口批准。
