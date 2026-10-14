# 第 81 号议题：唯一测试计划（第十一版已通过第二关限定复审）

## 版本与状态

- Requirement revision：第 81 号议题，2026-10-14 原始需求，https://github.com/ScholarWorkflow/professor-contact/issues/81。
- Implementation Plan：`issue-81-plan-r2-2026-10-14`，见 [issue-81-implementation-plan.md](issue-81-implementation-plan.md)。
- Test Plan revision：`issue-81-test-r11-2026-10-14`；唯一正式测试计划。
- 目标仓库基线：`3f66656c4e82c9f0235b6dd0937ae5b2333c48f9`；实际被测产品提交见下方执行记录。
- 产品实现提交为 `5412e5385975db2bcc6daf0740e0a2a3cf3d2445`。A—C 在该提交的干净生产者工作树执行；D 消费者通过 APM 安装的也是该提交。执行结果和固定版本记录见“第三关执行记录”。
- D 使用的合成夹具固定为 `RekiDunois/skills-test-fixtures` 提交 `fa3a03ed66be22e7191264462716e046c8b18e72`，Codex 配置文件为 `configs/codex-consumer.toml`；精确版本与配置摘要须随执行记录保存。
- 环境预检：`uv 0.12.22`、Python `3.14.6`、APM `0.29.0`、Codex CLI `0.162.0-alpha.17.2`、`yq v4.54.1`、`jq-1.8.2`、`direnv 2.37.1`、`curl 8.7.1`。Python 版本由 `UV_CACHE_DIR=/private/tmp/pc81-uv-cache uv run --offline --no-project python --version` 确认；A—D 的 `uv run` 均复用同一离线缓存目录 `/private/tmp/pc81-uv-cache`，不另建空缓存。以上为正式执行前的预检；本轮实际版本与配置摘要见下方记录。
- 第十版本地测试准备预检（2026-10-14，历史记录）：上列命令和版本本轮均复核可用，离线 Python 缓存目录存在且 Python `3.14.6` 可启动；`codex exec --help` 显示 `--sandbox <SANDBOX_MODE>`。测试计划、A—C 单元测试模块和 D 夹具准备器均存在；固定夹具提交 `fa3a03ed66be22e7191264462716e046c8b18e72` 中的 `configs/codex-consumer.toml` 包含 `sandbox_mode = "workspace-write"`。评估环境 `.envrc` 与 `EVAL_PORT` 可用（本轮未连接评估服务）。本轮未运行 A—C 测试、D 夹具准备器、`contact_state.py` 命令或评估请求；当时 D 仍待第二关限定复审。
- 第十一版计划修订：`sandbox_mode` 仅作为发给评估服务的 `codex exec` 命令参数；消费者项目配置副本移除该键，避免重复设置。第十一版仅修订 D 的配置和请求构造；该修订已通过第二关限定复审（[审核记录](https://github.com/ScholarWorkflow/professor-contact/pull/82#issuecomment-6170152859)）。
- 测试与证据边界遵守 [Test Engineer Rule](https://app.notion.com/p/rekidunois/Test-Engineer-Rule-3d80101a85f380d8a8f5ce528141e253) 和 [Project Consensus](https://app.notion.com/p/rekidunois/Project-Consensus-3d60101a85f3815a8c43f271f2b4d91d)。
- 第一关：**通过，沿用既有结论**，以 [第一关审核记录](https://github.com/ScholarWorkflow/professor-contact/pull/82#issuecomment-6164440577) 为准。第二关：第九版结论继续沿用；第十版重复设置问题见[限定复审记录](https://github.com/ScholarWorkflow/professor-contact/pull/82#issuecomment-6169418834)，第十一版修订已通过[第二关限定复审](https://github.com/ScholarWorkflow/professor-contact/pull/82#issuecomment-6170152859)。第三关历史执行结果：A—C 通过，D 无法判断；第十一版评估前置检查记录如下。

## 必测业务目标：本次验收范围的上限

| 编号 | 业务目标 | 场景与输入 | 预期结果 | 唯一主要检查方式 |
| --- | --- | --- | --- | --- |
| A | R1：合法格式写入后能被同一 runner 复用 | 合成教授本地邮件包、有效 `info.json` / `boshu_analysis.json`、完整且已实际核验的 8 项缓存；指纹直接来自初始 `stage5-plan` 的只读写入提示；时间为 `now_utc()` 格式 | 再调用相同教授的初始 `stage5-plan` 得到 `verify: ok`，无需再次核验；两项提示的路径和整数秒与 `verify_state()` 相符；同一调用中原有 `verify` 与 `jobs` 字段保持可消费 | 生产者仓库现有 `unittest` 和 `contact_state.py stage5-plan` 合成场景断言 |
| B | R2：格式错误指明字段且不得误判成功 | 保持源文件不变，分别把 `info_json` 指纹时间写成浮点秒、把 `boshu_analysis` 路径改为不同表示、把 `verified_at` 写成带小数秒或 `+00:00` UTC | 各次 `verify` 都需要重核；指纹错误保留 `stale_fingerprint`，时间错误保留 `bad_timestamp`，并在附加诊断中指出准确字段及 `format_incompatible`；不会产生 `verify: ok` | 同一组参数化 `unittest` 按各字段读取 `stage5-plan` 返回值 |
| C | R2 及既有安全边界：源记录不匹配和超期拒绝 | 对原本有效缓存，分别在缓存写入后改变一个实际源文件的整数修改时间；另保持指纹一致但把 `verified_at` 设置为距今 31 天 | 前者 `stale_fingerprint`，诊断为对应字段的 `recorded_mtime_mismatch`；后者 `expired`、字段 `verified_at`、`age_expired`；两者均不放行。不能宣称由元数据不符证明内容被修改 | 同一组生产者 `unittest` 断言当前 runner 的初始计划结果 |
| D | R3：前置源缺失时停止不变输入的重核，且不越过门禁 | 独立合成项目中先用齐全的两份源文件和有效缓存建立一位教授的本地邮件包，随后仅移走 `boshu_analysis.json`；保留旧缓存、完整模板、邮件包和其他输入。经正式初始 `stage5-plan` 确认实际理由是 `missing_source`（不是 `missing`、`missing_email_pack` 或联系方式快照失效）；再从已安装的 Codex 生产入口触发正式 Stage 5 教授 owner | 初始计划给该教授 `verify: needs_recheck:missing_source`，写入提示为 `null`，诊断指出 `source_fingerprints.boshu_analysis`；因 Stage 5 无权重建前置源，代理直接以 `needs_refresh` 和对应原因/字段结束，不对不变输入反复执行 Step 2.5，不生成模型结果、不调用 finalize、不写邮件。此处只检查当前教授的停止行为 | 一次目标 Codex 消费者运行，检查最终业务 JSON、原始初始 plan 和目标邮件文件；从现有执行记录只检查该教授必要的 `stage5-plan`/Step 2.5/finalize 调用，确认缺源后没有再重核；不认证整个委派过程 |

B 的四种输入是议题明确列出的写入不一致表现；C 的元数据变化与超期是议题要求**继续拒绝**的两条边界。D 只为代理无法修复前置源时的无进展停止安排一次运行，不增加多模型比较、全流程回归或通用委派认证。此次固定场景以缺源后的**首次计划即停止**检查 R3 的不可修复分支，避免依赖修改用户提示词或故意注入错误缓存写入来制造循环。既有 `test_contact_evidence_ladder.py` 的受保护证据行为未被本修复改变，除非实施产生实际影响，否则沿用其现存结果，不另行重复证明。

## 实施与执行的实际分工

1. **计划审核先行**：只有实施计划按 Plan Reviewer Rule 被正式审核为 `APPROVED` 后，产品实现者才修改代码与代理指令；测试计划由有权人员确认本页 A—D 的范围（第一关）。
2. **测试代码**：本地测试工程师新增 `.apm/skills/professor-contact/tests/test_issue81_verify_cache_contract.py`，A—C 共三个测试方法，复用 `test_contact_state.py` 的合成夹具，并以实际 `contact_state.py stage5-plan` 输出作断言。B 方法包含四个子场景；C 方法包含修改整数修改时间和 31 天缓存两个子场景。不会接触真人资料，也不增加 D 以外的正式 Codex 场景。
3. **D 合成资料准备器**：新增 `.apm/skills/professor-contact/tests/runtime/prepare_issue81_missing_source_fixture.py`。它只在指定消费者下生成单教授合成包、模板和 8 项缓存；通过检查合成文件、8 个缓存项目及源路径/整数修改时间确认夹具已写好，然后仅移走 `boshu_analysis.json` 并确认旧缓存仍在。准备器不调用 `stage5-plan` 或其他产品入口；缺源后的首次 plan、`missing_source`、准确字段和 `null` 写入提示只在 D 的正式 Codex 消费者运行中观察。准备失败时停止，不发送正式请求。
4. **A—C 准确命令**：在产品提交已固定且干净的生产者工作树中创建本轮独立运行目录，从测试目录执行。第 4—9 步的代码块在同一个 shell 中按顺序运行，以保留 `PC81_*` 变量；需要切换目录的命令放在子 shell 中，不改变主 shell 的当前目录。A—D 命令都复用预检过的离线 Python 缓存 `/private/tmp/pc81-uv-cache`：

   ```sh
   set -eu
   PC81_RUN_ROOT="$(mktemp -d /private/tmp/issue81-tests-XXXXXX)"
   PC81_PRODUCER_ROOT="$(pwd)"
   PC81_TEST_DIR="$PC81_PRODUCER_ROOT/.apm/skills/professor-contact/tests"
   test -z "$(git -C "$PC81_PRODUCER_ROOT" status --porcelain)"
   {
     printf 'product_sha='
     git -C "$PC81_PRODUCER_ROOT" rev-parse HEAD
     printf 'uv='
     uv --version
     printf 'python='
     UV_CACHE_DIR=/private/tmp/pc81-uv-cache uv run --offline --no-project python --version
   } > "$PC81_RUN_ROOT/versions.txt"
   set +e
   (cd "$PC81_TEST_DIR" && \
     PC81_RUN_ROOT="$PC81_RUN_ROOT" \
     UV_CACHE_DIR=/private/tmp/pc81-uv-cache \
     uv run --offline --no-project python -m unittest -v \
       test_issue81_verify_cache_contract) \
     > "$PC81_RUN_ROOT/unittest.log" 2>&1
   PC81_TEST_EXIT=$?
   set -e
   printf '%s\n' "$PC81_TEST_EXIT" > "$PC81_RUN_ROOT/exit-code.txt"
   ```

   以该次进程退出码和日志记录测试数、失败；`versions.txt` 保存产品 SHA、`uv` 与 Python 版本。单元测试使用标准库；临时项目由 `TemporaryDirectory` 自动清除，日志仅保留在独立运行目录。离线解释器无法启动时记为无法判断，不临时下载或换解释器。
5. **D 固定版本、安装与配置**：D 必须等产品实现提交和第二关通过。用全新 `$PC81_RUN_ROOT`，生产者仓库、其 worktree、消费者、夹具仓库互不嵌套；按下列步骤核对精确提交并安装：

   ```sh
   set -eu
   PC81_RUN_ROOT="$(mktemp -d /private/tmp/issue81-eval-XXXXXX)"
   PC81_PRODUCER_ROOT="/绝对路径/干净的生产者工作树"
   PC81_PRODUCT_SHA="实施后的产品提交 SHA"
   # 工作树位于项目父目录的 worktree/<name> 下；沿两级上级找到现有评估环境。
   PC81_EVAL_ENV_ROOT="$(cd "$PC81_PRODUCER_ROOT/../.." && pwd)"
   test -f "$PC81_EVAL_ENV_ROOT/.envrc"
   test "$(git -C "$PC81_PRODUCER_ROOT" rev-parse HEAD)" = "$PC81_PRODUCT_SHA"
   test -z "$(git -C "$PC81_PRODUCER_ROOT" status --porcelain)"
   PC81_FIXTURES_ROOT="$PC81_RUN_ROOT/skills-test-fixtures"
   git clone https://github.com/RekiDunois/skills-test-fixtures.git "$PC81_FIXTURES_ROOT"
   git -C "$PC81_FIXTURES_ROOT" fetch origin fa3a03ed66be22e7191264462716e046c8b18e72
   git -C "$PC81_FIXTURES_ROOT" checkout --detach fa3a03ed66be22e7191264462716e046c8b18e72
   test "$(git -C "$PC81_FIXTURES_ROOT" rev-parse HEAD)" = fa3a03ed66be22e7191264462716e046c8b18e72
   test -z "$(git -C "$PC81_FIXTURES_ROOT" status --porcelain)"
   {
     printf 'product_sha='
     git -C "$PC81_PRODUCER_ROOT" rev-parse HEAD
     printf 'fixture_sha='
     git -C "$PC81_FIXTURES_ROOT" rev-parse HEAD
     printf 'uv='
     uv --version
     printf 'python='
     UV_CACHE_DIR=/private/tmp/pc81-uv-cache uv run --offline --no-project python --version
     printf 'apm='
     apm --version
     printf 'codex='
     codex --version
     printf 'yq='
     yq --version
   } > "$PC81_RUN_ROOT/versions.txt"
   PC81_CONSUMER="$PC81_RUN_ROOT/consumer"
   mkdir -p "$PC81_CONSUMER"
   (cd "$PC81_CONSUMER" && apm init -y --target codex)
   (cd "$PC81_CONSUMER" && apm install "https://github.com/ScholarWorkflow/professor-contact.git#$PC81_PRODUCT_SHA" --target codex --trust-transitive-mcp)
   PC81_EXPECTED_SHA="$PC81_PRODUCT_SHA" yq -e '.dependencies[] | select(.name == "professor-contact") | .resolved_commit == strenv(PC81_EXPECTED_SHA)' "$PC81_CONSUMER/apm.lock.yaml"
   ```

   仅合并隔离消费者中的项目配置和固定夹具配置，保留安装生成的其余设置：

   ```sh
   set -eu
   PC81_TEST_CONFIG="$PC81_CONSUMER/.codex/config.toml"
   PC81_SANDBOX_MODE="$(yq -p toml -r '.sandbox_mode' "$PC81_FIXTURES_ROOT/configs/codex-consumer.toml")"
   test "$PC81_SANDBOX_MODE" = workspace-write
   yq eval-all -p toml -o toml '. as $item ireduce ({}; . * $item) | del(.sandbox_mode)' \
     "$PC81_TEST_CONFIG" "$PC81_FIXTURES_ROOT/configs/codex-consumer.toml" \
     > "$PC81_RUN_ROOT/config.toml"
   yq -p toml -e '.model == "gpt-6-luna" and .model_reasoning_effort == "low" and has("sandbox_mode") == false' \
     "$PC81_RUN_ROOT/config.toml"
   cp "$PC81_RUN_ROOT/config.toml" "$PC81_TEST_CONFIG"
   printf 'eval_sandbox_mode=%s\n' "$PC81_SANDBOX_MODE" >> "$PC81_RUN_ROOT/versions.txt"
   ```

   `versions.txt` 记录实际产品/夹具提交 SHA、`uv`、Python、Codex、APM、`yq` 版本和评估请求使用的 `sandbox_mode`；同时保存不含 `sandbox_mode` 的项目配置文件副本。不得覆盖个人配置；所需项目授权若未预先存在，停止并记无法判断。

   **隔离消费者写入前提**：本次只在消费者内生成教授交接文件，所需沙盒范围为 `workspace-write`。固定夹具的 `configs/codex-consumer.toml` 是该值的唯一来源；它只用于确定发给评估服务的 `codex exec` 命令参数，不复制到消费者项目配置。评估服务执行时，Codex 对未受信任项目可能跳过项目级 `.codex/config.toml`，所以请求中的 `--sandbox` 显式指定写入范围。参照 [knowledge-tools PR #5 的正式执行说明](https://github.com/ScholarWorkflow/knowledge-tools/blob/feat/personal-knowledge-runtime/tests/PR5-TEST-RECIPE.md) 第 7 节。该命令参数只确定沙盒写入范围，**不授予项目信任，也不保证其它项目级配置已加载**。不新增独立权限配置、不设置 `trust_level`、不修改个人配置，不使用 `danger-full-access`。项目不受信任而导致已安装技能或代理不可用时按现有环境阻断记无法判断，不靠增加权限或改提示词绕过。

6. **D 资料准备与前置检查**：在干净消费者内用实施提交附带的准备器，输出全部放在本轮运行目录：

   ```sh
   set -eu
   PC81_PROGRAM_ROOT="$PC81_CONSUMER/testdata/program"
   UV_CACHE_DIR=/private/tmp/pc81-uv-cache uv run --offline --no-project python \
     "$PC81_PRODUCER_ROOT/.apm/skills/professor-contact/tests/runtime/prepare_issue81_missing_source_fixture.py" \
     --consumer-root "$PC81_CONSUMER" \
     --program-root "$PC81_PROGRAM_ROOT" \
     --output-dir "$PC81_RUN_ROOT/preflight"
   PC81_EMAIL_PACK="$(jq -r '.email_pack' "$PC81_RUN_ROOT/preflight/fixture-manifest.json")"
   PC81_TEMPLATE="$(jq -r '.template' "$PC81_RUN_ROOT/preflight/fixture-manifest.json")"
   jq -e --arg program "$PC81_PROGRAM_ROOT" --arg pack "$PC81_EMAIL_PACK" \
     '.program_root == $program and .email_pack == $pack' \
     "$PC81_RUN_ROOT/preflight/fixture-manifest.json"
   test ! -e "$PC81_PROGRAM_ROOT/boshu_analysis.json"
   ```

   准备器只写合成文件并检查夹具结构：缓存有 8 个项目、源路径和整数修改时间与合成文件相符，移走的只有 `boshu_analysis.json`，旧缓存及邮件输入仍保留。它不运行 `contact_state.py`。缺源计划的 `needs_recheck:missing_source`、`verify_write_hints[教授] == null` 及诊断字段 `source_fingerprints.boshu_analysis` / `source_unavailable` 由下面 D 正式运行中的初始 `stage5-plan` 观察；准备阶段不得预先调用目标产品入口。如果夹具准备失败则停止，不发送 Codex 请求。

7. **D 正式请求**：正式请求提示固定写入 `$PC81_RUN_ROOT/prompt.txt`，不改写其中的路径：

   ```text
   请使用已安装的 professor-contact 工作流，对程序目录 <PC81_PROGRAM_ROOT> 中的教授邮件包 <PC81_EMAIL_PACK> 使用模板 <PC81_TEMPLATE> 执行阶段 5 首封邮件模式。本次未提供用户选择。
   ```

   将上文三个占位符替换为该次绝对路径并保存为 `$PC81_RUN_ROOT/prompt.txt`。以下步骤只在本机通过标准库 `shlex.join` 构造评估请求；`command` 字段包含 `codex exec` 的参数，由评估服务远端执行，本机不运行该命令。`timeout` 固定为 900 秒：

   ```sh
   test "$PC81_SANDBOX_MODE" = workspace-write
   UV_CACHE_DIR=/private/tmp/pc81-uv-cache uv run --offline --no-project python -c 'import json, pathlib, shlex, sys; consumer, prompt_file, output, sandbox_mode = sys.argv[1:]; argv = ["--json", "--skip-git-repo-check", "--sandbox", sandbox_mode, "--cd", consumer, "--", pathlib.Path(prompt_file).read_text(encoding="utf-8").strip()]; pathlib.Path(output).write_text(json.dumps({"command": shlex.join(argv), "timeout": 900}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")' "$PC81_CONSUMER" "$PC81_RUN_ROOT/prompt.txt" "$PC81_RUN_ROOT/request.json" "$PC81_SANDBOX_MODE"
   jq -e '.timeout == 900 and (.command | startswith("--json ") and contains("--sandbox workspace-write "))' "$PC81_RUN_ROOT/request.json"
   ```

   只把固定夹具配置中的沙盒值通过 Codex 支持的 `--sandbox` 参数发送给评估服务；消费者项目配置不再重复设置该值。不在命令中另设模型、推理、信任或 MCP 覆盖，也不传 `--ephemeral`。`--cd` 仍准确指向隔离消费者。执行前确认这个消费者已有所需的 Codex 项目授权；如授权不存在则停止，不写个人设置。显式沙盒值不能代替项目信任或产品核验结果。

   只向当前已配置的评估服务发送一次：

   ```sh
   printf 'not_run\n' > "$PC81_RUN_ROOT/curl-exit-code.txt"
   direnv_rc=0
   direnv exec "$PC81_EVAL_ENV_ROOT" sh -c 'curl_rc=0; curl --connect-timeout 10 --max-time 930 -sS -X POST "http://127.0.0.1:${EVAL_PORT}/eval" -H "Content-Type: application/json" --data-binary @"$1" -o "$2" -w "%{http_code}\n" > "$3" || curl_rc=$?; printf "%s\n" "$curl_rc" > "$4"' sh "$PC81_RUN_ROOT/request.json" "$PC81_RUN_ROOT/response.raw.tmp" "$PC81_RUN_ROOT/http-status.txt" "$PC81_RUN_ROOT/curl-exit-code.txt" || direnv_rc=$?
   printf '%s\n' "$direnv_rc" > "$PC81_RUN_ROOT/direnv-exit-code.txt"
   ```

   从评估服务现有记录读取结果，不启动、停止或重启服务，也不直接在 shell 执行 `codex`。`response.raw.tmp` 只作为本轮筛选输入；下一段命令无论成功或失败都会删除它，不重发请求：

   ```sh
   if test "$(cat "$PC81_RUN_ROOT/direnv-exit-code.txt")" != 0; then
     jq -n --arg exit "$(cat "$PC81_RUN_ROOT/direnv-exit-code.txt")" \
       '{direnv_exit_code:($exit|tonumber),outcome:"eval_environment_error"}' \
       > "$PC81_RUN_ROOT/evidence.json"
   elif test "$(cat "$PC81_RUN_ROOT/curl-exit-code.txt")" = not_run; then
     jq -n '{outcome:"eval_environment_error"}' > "$PC81_RUN_ROOT/evidence.json"
   elif test "$(cat "$PC81_RUN_ROOT/curl-exit-code.txt")" != 0; then
     jq -n --arg http "$(cat "$PC81_RUN_ROOT/http-status.txt")" \
       --arg curl "$(cat "$PC81_RUN_ROOT/curl-exit-code.txt")" \
       '{http_status:$http,curl_exit_code:($curl|tonumber),outcome:"transport_error"}' \
       > "$PC81_RUN_ROOT/evidence.json"
   elif test "$(cat "$PC81_RUN_ROOT/http-status.txt")" != 200; then
     jq -n --arg http "$(cat "$PC81_RUN_ROOT/http-status.txt")" \
       '{http_status:$http,outcome:"http_error"}' \
       > "$PC81_RUN_ROOT/evidence.json"
   elif jq -e --arg http "$(cat "$PC81_RUN_ROOT/http-status.txt")" '
     if (has("passed") | not)
       or (has("version") | not)
       or (.passed | type != "boolean")
       or (.output | type != "object")
       or (.output.exit_code | type != "number")
       or (.output.termination_reason | type != "string")
       or (.output.thread_id | type != "string")
       or (.output.app_server_events | type != "array")
     then error("required eval response structure missing")
     else
       .output.thread_id as $root_thread
       | .output.app_server_events as $events
       | [$events[]
           | select(.direction == "recv"
               and .message.method == "item/completed"
               and .message.params.item.type == "commandExecution"
               and ((.message.params.threadId | type) == "string")
               and ((.message.params.item.command // "") | contains("contact_state.py")))] as $commands
       | ($commands | map(.message.params.threadId) | unique) as $command_threads
       | ($command_threads | map(select(. != $root_thread))) as $owner_threads
       | {
           http_status: $http,
           passed,
           version,
           api_error: (.error // null),
           eval: {
             exit_code: .output.exit_code,
             termination_reason: .output.termination_reason,
             product_commands: [$commands[]
               | {
                   runtime_seq,
                   thread_id: .message.params.threadId,
                   command: .message.params.item.command,
                   cwd: .message.params.item.cwd,
                   exitCode: .message.params.item.exitCode,
                   aggregatedOutput: (if (.message.params.item.command | contains("stage5-plan"))
                     then .message.params.item.aggregatedOutput else null end)
                 }],
             owner_final_messages: [$owner_threads[] as $thread_id
               | ($events
                   | map(select(.direction == "recv"
                       and .message.method == "item/completed"
                       and .message.params.threadId == $thread_id
                       and .message.params.item.type == "agentMessage"))
                   | sort_by(.runtime_seq)
                   | last) as $final
               | {
                   thread_id: $thread_id,
                   runtime_seq: ($final.runtime_seq // null),
                   text: ($final.message.params.item.text // null)
                 }]
           }
         }
     end' "$PC81_RUN_ROOT/response.raw.tmp" > "$PC81_RUN_ROOT/evidence.json"; then
     :
   else
     jq -n --arg http "$(cat "$PC81_RUN_ROOT/http-status.txt")" \
       '{http_status:$http,outcome:"invalid_or_unusable_response"}' \
       > "$PC81_RUN_ROOT/evidence.json"
   fi
   rm -f "$PC81_RUN_ROOT/response.raw.tmp"
   ```

   仅在 `$PC81_RUN_ROOT` 保存本次请求、`direnv`/HTTP/`curl` 状态、固定配置副本、按非 root 命令线程筛出的 owner 最终业务消息、初始 `stage5-plan` 输出、相关原始执行事件的必要字段（`runtime_seq`、`thread_id`、`command`、`cwd`、`exitCode`；只有 `stage5-plan` 事件保留 `aggregatedOutput`）、目标邮件目录检查结果和必要的版本号。评估服务原始命令事件的输出字段为 `aggregatedOutput`，不是 `output.text`；owner 最终消息从相同 `thread_id` 的原始 `agentMessage` 事件取得，不使用只含 root 线程的兼容事件列表。筛选命令校验 `passed`、`version`、`output.exit_code`、`output.termination_reason`、`output.thread_id` 和 `output.app_server_events`；必需结构缺失时 `jq -e` 失败并记录 `invalid_or_unusable_response`。按 `runtime_seq` 和 `thread_id` 区分调用。不复制完整响应、完整服务记录或无关环境诊断；不新增采集器。环境包装失败时只记录 `direnv` 退出码；传输失败时只记录 HTTP 状态与 `curl` 退出码；响应无法解析或不含所需结构时只记录状态及 `invalid_or_unusable_response`，随后删除原始临时文件。

8. **D 唯一观察点**：请求结果可解析且夹具清单存在时，从清单读取教授目录并在该目录检查产物：

   ```sh
   PC81_PROFESSOR_DIR="$(jq -r '.professor_dir' "$PC81_RUN_ROOT/preflight/fixture-manifest.json")"
   if test -d "$PC81_PROFESSOR_DIR"; then
     find "$PC81_PROFESSOR_DIR" -maxdepth 1 -type f \( -name '*.md' -o -name '*.txt' -o -name '套磁邮件状态.json' \) -print > "$PC81_RUN_ROOT/target-mail-files.txt"
     if test -s "$PC81_RUN_ROOT/target-mail-files.txt"; then printf 'present\n'; else printf 'absent\n'; fi > "$PC81_RUN_ROOT/target-mail-check.txt"
   else
     printf 'directory_missing\n' > "$PC81_RUN_ROOT/target-mail-check.txt"
   fi
   ```

   随后从 `owner_final_messages` 中与该教授命令事件同一 `thread_id` 的最终业务 JSON，以及相同线程的 `commandExecution` 记录检查：正式结果为 `needs_refresh`、原因 `missing_source`、字段 `source_fingerprints.boshu_analysis`；其初始 `stage5-plan` 保留为 `needs_recheck:missing_source`、写入提示为 `null`，且其余诊断字段与计划相符；owner 只执行这一份缺源初始计划，没有在源未变时重复 Step 2.5 或重跑计划，没有生成邮件结果、调用 `stage5-finalize`，`target-mail-check.txt` 为 `absent` 且 `target-mail-files.txt` 为空。按筛选后的结构字段、`runtime_seq`、`thread_id`、`command`、`cwd`、`exitCode`、`aggregatedOutput` 和实际文件判断，不以自然语言自述代替。若现有记录不能区分上述调用，记无法判断；不新增采集器、不宣称通过。

9. **失败、重试、清理与结果**：A—C 各执行一次；环境或解释器无法启动则记无法判断，不因业务断言失败而重跑。D 每次获批的固定方案正式 `/eval` 最多一次；环境包装、传输、服务、配额、模型、写入权限或记录不完整时按现有状态记无法判断或未执行，不在同一尝试内重发请求。旧版 D 的无法判断记录保持不变；第十、十一版启动参数与配置接线变化属于方案修订，第二关限定复审通过后，再由本地执行工程师在独立目录进行**一次新的正式尝试**，不得将它记作相同配置的重试或覆盖旧记录。业务结果不符记业务失败。仅保留失败所需的 `direnv`/HTTP/`curl` 状态及筛选后的简短错误字段，不保留完整失败响应；消费者、配置、请求和筛选后的证据都留在独立 `/private/tmp/issue81-*` 下，不复制用户资料、不写回生产者仓库。结果只分为通过、业务失败、无法判断、未执行，并记录实现 SHA、夹具 SHA、版本、配置摘要与执行码。

## 第三关执行记录

- 产品提交：`5412e5385975db2bcc6daf0740e0a2a3cf3d2445`。执行时生产者工作树干净，路径为项目父目录下的 `worktree/issue-81-implementation-20261014`。
- A—C：结果**通过**。运行目录 `/private/tmp/issue81-tests-FJIPI7`；命令退出码 `0`，以下 3 个测试方法均通过：`test_a_actual_plan_hints_seed_a_reusable_complete_cache`、`test_b_noncanonical_values_keep_the_reason_and_report_the_field`、`test_c_changed_mtime_and_31_day_cache_remain_rejected`。版本：`uv 0.12.22`、Python `3.14.6`。日志与版本记录保存在该目录。
- D 固定输入：夹具提交 `fa3a03ed66be22e7191264462716e046c8b18e72`；运行目录 `/private/tmp/issue81-eval-qZWvLG`；安装产品提交与上列一致。版本：`uv 0.12.22`、Python `3.14.6`、APM `0.29.0`、Codex CLI `0.162.0-alpha.17.2`、`yq v4.54.1`、`jq-1.8.2`、`direnv 2.37.1`、`curl 8.7.1`。消费者配置 SHA-256：`923ef5e3e57b6f0af179ceb0ee65aee1ca79bbb4d32de5c1526f53ea9c927c82`。登录状态检查退出码为 `0`。
- D 请求只发送一次；HTTP `200`、`curl` 退出码 `0`、评估结果 `passed: true`、进程退出码 `0`、终止原因 `completed`。已筛选的产品事件只有一条 `stage5-list-inputs`：`runtime_seq=27065`、事件线程 `01a13a20-fef5-7c81-8e5e-4baac36eeb33`、退出码 `0`。没有 `stage5-plan` 事件，也没有可用的非根 owner 最终消息。目标邮件目录检查为 `absent`，文件数为 `0`。
- D 结果：**无法判断**。现有筛选记录未提供预期的初始 `stage5-plan` 输出、owner 业务 JSON 或对应的停止过程，无法判断缺源诊断及停止规则；不宣称通过，不重发请求。原始响应已按计划删除，保留的筛选结果及执行码位于上述独立运行目录。
- D（r11 新尝试，2026-10-14）：**无法判断（评估未执行）**。候选实现提交为 `5412e5385975db2bcc6daf0740e0a2a3cf3d2445`，PR 当前头为 `d94f9efe4b2dda77d6069607ce9ff190013127a2`。隔离运行目录为 `/private/tmp/issue81-eval-foeXjl`，新消费者目录为 `/private/tmp/issue81-eval-foeXjl/consumer`。预检命令 `codex --version` 返回 `0.162.0-alpha.17.2`；`codex login status` 退出码为 `0`。按 D 第 5 步，在评估环境的 Codex 用户配置中只读检查该消费者路径的 `projects.<path>.trust_level`，结果为 `not_configured`。该消费者尚未获项目授权，因此按计划停止；没有安装 APM 包、克隆夹具、构造请求或发送 `/eval`，没有改写任何用户配置。预检结果见独立文件 `/private/tmp/issue81-eval-foeXjl/preflight-evidence.json`。旧版 D 的正式尝试记录保持不变。

## 禁止新增的测试要求

- 不测试所有合法 ISO-8601 时间变体的**接受**；本次选择明确的 `Z` 秒级输出，不扩大读取端解析能力。
- 不以哈希或额外数据判断文件内容是否实际变更，也不测跨进程竞争、缓存迁移或缓存整体重构。
- 不要求验证完整 Codex 委派拓扑、命令探测、线程数量、所有运行事件、所有代理中间消息或新增专用采集器。
- 不跑全部阶段 0—5、全部浏览器/模型供应商、全部教授及所有邮箱证据分支。
- 不修改产品保护或用户数据来让 D 获得通过结果。

**r11 相对 r10 只修订 D 的配置和评估请求构造：从固定夹具配置读取 `sandbox_mode`，从消费者项目配置中移除该键，只把该值放入发给评估服务的 Codex `--sandbox` 参数；明确 `command` 由评估端执行，本机只构造请求。保留 `--cd` 与现有评估入口，不授予项目信任。A—D 业务目标、固定输入、提示词、观察点、证据提取、产品实现及 A—C 既有通过结果不变。第十一版第二关限定复审已通过（见 issuecomment-6170152859）；第三关 D 仍为无法判断；不新增测试，不改写历史结果。**
