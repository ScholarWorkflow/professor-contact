# TP1.1 离线执行记录

- 日期：2026-10-29；基线 `ad096fe31a4b5694cbe47a40f37b621435e1eeec` 加本 PR 工作 diff，分支 `feat/stage5-email-chinese-translation`。
- 云端 Python unittest，无模型调用、安装、Mac操作或用户材料；synthetic fixture 临时目录由既有 BaseEnv 管理。
- T1/T2：`python -m unittest discover -s .apm/skills/professor-contact/tests -p 'test_stage5_email_translation.py' -v`，最终精确收集 2 项、exit 0、OK。观察双 md 正确位置/独立译文、txt 精确等于 translation_source、模板字节保留；stale/missing中译及手改md拒绝后产物/状态不变。
- T3：`cd .apm/skills/professor-contact/tests && python -m unittest test_stage5_immutable.TestStage5ImmutableTemplates.test_finalize_without_full_body_humanizer_preserves_fixed_segments -v`，1 项、exit 0、OK；包括新增无中文译文节断言。
- `git diff --check`：exit 0，无输出。
- 原始日志：当时的定向日志 `/tmp/stage5-email-translation-validation/T1-T2-targeted.log`、`T3.log`、`T2-structured.log` 已不在该目录（该目录后续被 2026-10-30 的全量回归日志占用），**无法再打开**。
  - 这不改变 T1–T3 的判定依据：本记录本身即按 Test Engineer Rule §5/§7 交付的执行记录，记的是当次实际命令与逐项结果，第三关可据此采用。
  - 2026-10-30 的全量回归日志 `shard3-final.log` 另含同名用例在同断言下通过（第 323 行 `test_both_translations_are_markdown_only`、第 324 行 `test_stale_missing_and_manual_changes_preserve_outputs`、第 84 行 `test_finalize_without_full_body_humanizer_preserves_fixed_segments`）。按本文件“范围外诊断”的定性，这些行只是**旁证**，不替代、也不升格为 T1–T3 的 Gate 证据。未重跑这两轮定向命令。
- 执行偏离保留：第一次新测试模块直接导入既有 TestCase，unittest 除 T1/T2 外额外收集 8 个既有 case，共 10 项 OK。原日志 `T1-T2.log` 同样已不在 `/tmp/stage5-email-translation-validation/`（与本条上一行的定向日志一起被后续运行覆盖，未另行归档）。随后改为模块导入阻止无关收集，按原批准范围精确执行 2+1；额外执行不是新增验收义务，不要求重复。
- T4：未执行；当前无已确认正式 consumer/eval/fixture路径，真实模型翻译语义/agent接线不能以离线合成中文代替。整体测试与合并结论不作 PASS。
- 以上为执行者事实记录，待独立 Gate 3/代码复核。

## T2 定向修订复验
独立 reviewer 要求使用已有 parse(result) 检查真实 JSON status/reason_code，而非 stdout 子串匹配。已在原三个失败场景作此最小修订：stale/missing 为 error，手改为 needs_decision，并分别精确核对原因码。仅执行 `cd .apm/skills/professor-contact/tests && python -m unittest test_stage5_email_translation.TestEmailTranslation.test_stale_missing_and_manual_changes_preserve_outputs -v`；1 项、exit 0、OK，当次日志 `/tmp/stage5-email-translation-validation/T2-structured.log`（现已不在该目录）。该次结论以本节记录为准；`shard3-final.log` 第 324 行同名用例 ok 仅为旁证，按范围外诊断对待。T1/T3 产品行为未改，沿用既有结果；T4仍未执行。

## 2026-10-30 全量回归与 T4 正式尝试

- 执行环境：Darwin（aarch64）；产品版本 `70e9f0cd6c35771a75ec73ab7617da5c27ac21c3`（执行时的 PR head，未改动产品代码）。当前 head 为 `35ef5a76`；`70e9f0cd..35ef5a76` 只改文档与计划记录，`scripts/` 与 `tests/` 零差异，因此下面这轮结果对当前 head 同样成立。解释器 `Python 3.12.13`（`uv run --python 3.12 --no-project python`），与 `.github/workflows/ci.yml` 的 `python-version: '3.12'` 一致。工作树 `git diff --check` exit 0、无输出；执行前后 `git status` 干净。

### 全量回归（范围外诊断，非计划执行结果）

**性质说明**：TP1.2 第 22 行写明本计划“不跑全仓回归”。下面这轮四 shard 全量运行是用户在执行本轮指示“把测试跑通”时要求的**范围外诊断**，未获计划批准、不在必测清单内，**不作为 Gate 证据或合并依据**；T1–T3 的正式判定仍以原定向用例为准。保留它是为了让“全仓是否可跑通”这一用户关注点有如实记录；如果验收决定人不追认，删除本节不影响任何必测项结果。

命令：先以 `uv run --python 3.12 --no-project python scripts/check_test_shards.py` 确认 `OK: 89 test modules across 4 shards, each with a stage`；再对每个 shard 在 `.apm/skills/professor-contact/tests` 下执行 `python -m unittest $(python ../../../../scripts/check_test_shards.py --print <shard>) -v`。

|shard|用例数|结果|
|---|---|---|
|shard1|389|OK|
|shard2|227|OK|
|shard3|295|OK|
|shard4|291|OK（6 skipped）|

合计 1202 项，全部 exit 0。原始日志 `/tmp/stage5-email-translation-validation/shard{1,2,3,4}-final.log`。

本 PR 的目标用例即在同一全量命令内收集到：T1/T2 `test_stage5_email_translation.py` 2 项 OK；T3 `test_stage5_immutable...test_finalize_without_full_body_humanizer_preserves_fixed_segments` 1 项 OK。这一句只说明目标用例在上述运行中同样通过，不把全量回归改称为必测项。

### 本地环境失败与处理（非产品缺陷，同属范围外诊断）

首轮用默认 `python3`（`/usr/bin/python3` 3.9.6）与未规整的 `TMPDIR` 运行时出现 5 个失败，全部在 `main`（`ad096fe3`，无本 PR 改动）上以同样方式复现，因此不是本 PR 引入的缺陷：

- `test_issue32_eval_request` 2 项：`runtime/build_issue32_eval_request.py` 使用 `tomllib`，3.9 无该模块（3.11+ 才有）。
- `test_stage2_input_router` 1 项（2 个 subTest）：`stage2_input_router.py` 对 `output_dir` 调用 `.resolve()`，与测试用未规整的临时目录路径不相等；macOS 上 `TMPDIR=/var/...` 是指向 `/private/var/...` 的符号链接。
- `test_stage2_chatgpt_handoff_text` 1 项：同一 `/private` 符号链接导致 `record['sources']['ABC']` 与 `str(Path)` 不等。

处理方式：改用与 CI 相同的 3.12，并把 `TMPDIR` 设为已解析的 `/private/var/folders/.../T/`。两处都是执行环境对齐，未修改产品、测试期望或断言；对齐后上述模块 42 项全部 OK。**未修改任何被测产品代码。**

### T4 正式模型观察：无法判断（请求完成但流程未进入 Stage 5）

按 TP1.2 §A–D 执行，环境绑定如下（真实值，已在 `/tmp` 外单独留存）：

- `PC155_RECIPE_ROOT=/Users/rekidunois/code/skill-repos-dev/worktree/professor-contact-pr155-execution-20261030`
- `PC155_EVAL_ENV_ROOT=/Users/rekidunois/code/skill-repos-dev`（`direnv exec` 提供 `EVAL_PORT=17902`，服务已在监听）
- `PC155_RUN_ROOT=/tmp/pc155-t4-0IBlYQ`；`PC155_PRODUCT_SHA=bbd62bba…`；APM 0.29.0 全新隔离 consumer
- `apm install` 成功：11 个 APM 依赖、7 个 MCP server；`yq` 核对 `.dependencies[] | select(.name=="professor-contact") | .resolved_commit` 等于固定 SHA（exit 0，`true`）；`.codex/agents/` 存在 exact named `professor-contact-email-generator.toml` 与 `professor-contact-email-validator.toml`；模型配置已按 §B 合并 `gpt-6-luna` / `low`。
- fixture 由 §C 既有 `_stage5_issue59_test_support.write_issue59_stage5_fixture` 生成单教授 + 两套合成模板，`case.doCleanups()` 已撤销 checker 注入；正式模型进程使用安装包的真实 checker。用 professor-research 的真实 `contact_evidence.py --check` 复核该 fixture：`{"result":"fresh",…,"professors":[{"name":"試験 教授","result":"fresh"}]}`，exit 0。

请求只发送一次（`pc155_request_rc=0`，HTTP 200，`response.json` 中 `output.exit_code=0`、`output.termination_reason=completed`、`backend=app-server`、`stderr` 为空）。但业务结果是**未生成邮件**：

- 根代理调用了 `stage5-list-inputs`（返回该教授 `status: ok`），随后调用 `stage5-partition-choices` 时把目标 id 写成简写 `DIR00001_1`，而原始 `choices.email_id` 是 `試験 教授::DIR00001::DIR00001_1`。
- 该次分配返回 `status: ok`，但该教授 `choices_rows: []`。根代理据 5.11 第 4/6 步判定不能把空行交给子代理冒充用户选择，因此**没有启动 professor-contact-email-generator**，也没有生成/校验邮件与重建总览。`child_thread_reads` 为 0，`教授研究/` 下无 `套磁邮件.md`/`套磁邮件状态.json`。
- 产物保留：`/tmp/pc155-t4-0IBlYQ/{request.json,response.json,http-status.txt,request-exit.txt,request.stderr,prompt.txt,fixture-paths.json}` 与 `consumer/stage5-run-20261030/{raw-choices.json,partition.json}`。

归因与结论：

- 这是**根代理的输入准备擦写**（把完整 `email_id` 简写成 idea 编号），不是产品缺陷，也不是用户业务输入不匹配。产品对合法完整 id 的行为已用同一安装包单独核对：`--owner <pack> '試験 教授::DIR00001::DIR00001_1'` → `choices_rows` 1 行；不传目标 id → 1 行；仅简写 `DIR00001_1` → `choices_rows: []`（与该次运行一致）。该观察只是失败归因的定位，不是新的验收项。
- 按 `PROJECT_CONSENSUS.md` §基础设施重试与停止与 TP1.2 §D「只发送一次；超时、网络中断或不确定时保存同一请求后人工决定」，未自动重发第二次正式请求。
- 因此 T4 记为**无法判断**（真实模型通路与 agent 接线未产生可判定的最终产物），T4 Gate 3 仍未执行；T1–T3 离线机械结果不能替代 T4 的翻译语义与实际模型接线。整体测试与合并结论仍不作 PASS。
