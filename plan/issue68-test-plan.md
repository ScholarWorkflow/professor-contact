# 第68号议题测试计划：按最新规则精简

版本：`issue-68-test-plan-r62-2026-10-11`（计划设计与第二关口已通过；2026-10-11 同步最新执行记录，第三关口待审核）。

目标仓库：`ScholarWorkflow/professor-contact`；拉取请求：[第72号](https://github.com/ScholarWorkflow/professor-contact/pull/72)。本文件是唯一完整计划，取代第六十一版；原业务目标与检查方法不变。最新正式执行及补查已有记录；本文件不授权新增正式请求。

沿用甲至辛8组：甲至庚复用历史7个证明方法内43个组件结果；辛沿用原6个观察点。128项、6项和27项范围外自动化不恢复，自动化重跑0项。

## 1. 正式依据与范围

- [当前需求](https://github.com/ScholarWorkflow/professor-contact/issues/68)：第五阶段按教授独立处理，一位教授失败不影响另一位教授的合法结果。
- [验收第四版](https://github.com/ScholarWorkflow/professor-contact/issues/68#issuecomment-5981562292)：`R68-1`至`R68-8`、`AD68-1`至`AD68-5`。
- 测试范围、证据边界和修订方式以任务工作区的 `Test Engineer Rule.md` 为准；安装、隔离和配置遵守 `PROJECT_CONSENSUS.md`。
- 假定教授姓名唯一，不测试同名教授。前四阶段、历史迁移、通用写锁、邮件文案质量、第67号议题和第48号议题不属于本轮新增测试。

## 2. 必测清单

| 项目 | 输入或场景 | 预期结果 | 唯一检查入口 |
| --- | --- | --- | --- |
| 甲：本地包是第五阶段唯一事实来源；`R68-1、R68-6` | 本地包有效、缺失或与旧全局包不同 | 只使用显式本地包；缺失时拒绝；旧全局包不改变结果 | 直接复用历史 `P1` 的4项结果，不重跑 |
| 乙：指定单邮件兼容与自身校验；`R68-2` | 选择一封邮件，另有未选中邮件或目标自身错误 | 未选中邮件不阻断目标；目标自身错误仍拒绝；只更新目标输出 | 直接复用历史 `P2` 的4项结果，不重跑 |
| 丙：同教授整批提交；`R68-3` | 当前教授多封邮件全部有效或其中一封不满足条件 | 全部有效才提交，不拆成逐邮件部分提交 | 直接复用历史 `P3` 的2项结果，不重跑 |
| 丁：教授和校验状态隔离；`R68-4、R68-7、R68-8` | 一位教授成功，另一位有输入、选择或输出错误 | 成功结果保留；错误只属于对应教授 | 直接复用历史 `P4` 的2项结果；本次正常产物归属由辛观察 |
| 戊：总览独立派生与人工修改保护；`R68-5、AD68-2` | 本地结果完成后重建总览；总览缺失、损坏或存在人工修改 | 总览可重建；冲突或失败不回滚教授结果 | 直接复用历史 `P5` 的7项结果；本次总览内容由辛观察 |
| 己：独立启动只读发现；`AD68-3` | 有效本地包与损坏包并存 | 有效包仍可选；坏包只影响所属教授；发现不写业务文件 | 直接复用历史 `P6` 的4项结果，不重跑 |
| 庚：选择确定归属并保持原值；`AD68-4、AD68-5` | 显式目录、唯一候选、真实歧义、不同教授使用相同邮件编号 | 按目录与编号归属；歧义不广播；一位分配失败不阻断另一位；路径和行值不重建 | 直接复用历史 `P7` 的20项结果，不重跑 |
| 辛：两位教授的第五阶段独立处理；`R68-4、R68-8、AD68-1、AD68-5` | 两位姓名不同的教授，各有本地包、完整选择和不同研究内容 | 两次准确委派和分别交接；各自产生首封、跟进邮件与本地状态并如实记录审核结论；两人结束后最多一次重建含双方结果的总览；清理本次临时文件并分别汇报。`fail_after_2_rounds` 不使本议题失败 | 第4.4节原6项观察；不要求邮件审核 `pass`，不读取加密代理消息，不新增请求 |

此前所有正式尝试及失败保留在[执行记录](issue68-test-execution-2026-10-09.md)。2026-10-11 运行的产品版本为 `7472fd3688b11be199b333fda8caabdb00c7ff92`；原六项观察点的既有结果及同次消费者补查均已写入执行记录，六项均记录为通过。首封和跟进邮件审核状态为 `fail_after_2_rounds`，符合本议题的流程完成判定，但邮件仍不可视为可发送稿。本轮未新发正式请求，第三关口仍待审核。

## 3. 复用结果与删除的重复义务

历史结果来自 [保留记录](../.apm/skills/professor-contact/tests/runtime/evidence/issue68-d1-r29-history.json)：生产提交为 `35f2785b4d13783683860db910a36add2347bd29`，包含7个证明方法和方法内43个组件结果，`P1` 至 `P7` 均通过。当前产品源码基线为 `6169c87c610905415ab9c7145a5e791b5cd92ab1`。两者之间的影响判断如下：

| 历史证明 | 当前结论 | 提交差异影响 |
| --- | --- | --- |
| `P1` 本地包唯一事实来源 | 继续复用 | 阶段5读取、缺包拒绝和旧全局包处理函数未变；共享目录约束被拆成返回原因的辅助函数，并新增 `OSError` 失败关闭，但历史用例中的合法目录仍通过、越界目录仍以同一原因拒绝 |
| `P2` 定向邮件隔离 | 继续复用 | `stage5-plan`、`stage5-finalize` 的定向选择和写入逻辑未变 |
| `P3` 同教授整批提交 | 继续复用 | 教授内批量校验、原子写入和回滚逻辑未变 |
| `P4` 教授状态隔离 | 继续复用 | 教授本地状态与校验写入逻辑未变；后续阶段1至4的本地化修改不改变阶段5状态提交函数 |
| `P5` 总览独立派生 | 继续复用 | `stage5-rebuild-overview` 的读取、冲突保护和写入逻辑未变 |
| `P6` 独立启动发现 | 继续复用 | `stage5-list-inputs` 的只读发现逻辑未变；它使用的目录约束重构对历史合法目录、越界目录的预期结果不变 |
| `P7` 选择归属 | 继续复用 | 分配和选择消费的可执行逻辑未变；`b39a425` 只改命令帮助文字，`stage5_immutable.py` 只改说明文字 |

`35f2785` 至旧基线的复用判断保持。此后根技能、教授代理、流程说明和新增的 Codex 专属委派说明均为本议题有意修改的调用约定；阶段5两个业务脚本的执行逻辑未变。实际委派和输出交给辛的原6项检查，不为文档改变重跑甲至庚。

旧参考基线 `6169c87` 的相等比较只覆盖 `contact_state.py`、`stage5_immutable.py` 两个未变的业务脚本。修改的根技能、教授代理、流程参考和目标专属说明随当前拉取请求安装，由辛的委派和结果直接观察；后续业务脚本若变更，才重新判断受影响的历史证明，不自动全量重跑。

下列结果只作开发和持续集成历史，不属于本轮必测清单、第二关口或第三关口的通过条件，也不再运行：

- 五模块128项回归；其中包含阶段2至4、第59号、第64号、第65号、第67号等本轮范围外测试。
- 请求构建器6项单元测试；正式发送前直接解析实际 `request.json` 已足够，不再测试测试工具本身。
- `test_stage3_stage4_caller_contract.py` 的27项调用约定测试；其中绝大多数属于阶段3、阶段4和第67号议题。

既有运行记录继续保留原事实，不删除、不把历史失败改成通过，也不把43个组件写成43个测试方法，或把上述161项写成当前验收数量。

## 4. 修复后正式请求的操作步骤

### 4.1 产品、消费者和配置

1. 在第72号拉取请求分支当前干净工作树运行：

   ```sh
   git fetch origin codex/issue-68-stage5-per-professor
   test -z "$(git status --porcelain)"
   PC68_RECIPE_ROOT="$(pwd)"
   PC68_PRODUCT_SHA="$(git rev-parse HEAD)"
   PC68_REFERENCE_PRODUCT_SHA="6169c87c610905415ab9c7145a5e791b5cd92ab1"
   test "$PC68_PRODUCT_SHA" = "$(git rev-parse FETCH_HEAD)"
   git diff --quiet "$PC68_REFERENCE_PRODUCT_SHA" "$PC68_PRODUCT_SHA" -- \
      .apm/skills/professor-contact/scripts/contact_state.py \
      .apm/skills/professor-contact/scripts/stage5_immutable.py
   ```

   任一检查失败时停止。`git fetch` 网络错误由人工决定重试或结束，代理不自动重试。根技能、教授代理、流程参考及 Codex 专属说明均随 `$PC68_PRODUCT_SHA` 安装；它们的有意修改不参加旧基线比较，按辛已有的委派、交接和结果检查观察，不新增专项静态断言。

2. 新建仓库外运行目录和干净消费者，按冻结提交正式安装：

   ```sh
   PC68_RUN_ROOT="$(mktemp -d /private/tmp/pc68-r58-20261010-XXXXXX)"
   PC68_CONSUMER="$PC68_RUN_ROOT/consumer"
   mkdir -p "$PC68_CONSUMER"
   cd "$PC68_CONSUMER"
   apm init -y --target codex
   apm install "https://github.com/ScholarWorkflow/professor-contact.git#$PC68_PRODUCT_SHA" --target codex --trust-transitive-mcp
   PC68_EXPECTED_SHA="$PC68_PRODUCT_SHA" yq -e '.dependencies[] | select(.name == "professor-contact") | .resolved_commit == strenv(PC68_EXPECTED_SHA)' apm.lock.yaml
   ```

   安装错误时立即停止并报告，由人工决定是否按原命令重试。人工要求重试时使用同一提交和原命令，在新的空消费者中开始。

3. 测试配置继续使用同一提交中的 `plan/issue68-eval-codex-config.toml`，只合入 `model = "gpt-6-luna"` 和 `model_reasoning_effort = "low"`：

   ```sh
   PC68_TEST_CONFIG_SOURCE="$PC68_RECIPE_ROOT/plan/issue68-eval-codex-config.toml"
   PC68_TEST_CONFIG="$PC68_CONSUMER/.codex/config.toml"
   yq eval-all -p toml -o toml '. as $item ireduce ({}; . * $item)' "$PC68_TEST_CONFIG" "$PC68_TEST_CONFIG_SOURCE" > "$PC68_RUN_ROOT/config.toml"
   yq -p toml -e '.model == "gpt-6-luna" and .model_reasoning_effort == "low"' "$PC68_RUN_ROOT/config.toml"
   cp "$PC68_RUN_ROOT/config.toml" "$PC68_TEST_CONFIG"
   ```

   沿用既有项目受信任入口，不重做配置载体、评估服务或工具能力测试。

### 4.2 复用已确认输入

复用第四十八版已经通过准备检查的合成输入，来源为 `/private/tmp/pc68-task-20261009.U3yrne1G/run-Yo9u50JZ/consumer`。只复制以下测试业务资料到新消费者，不复制旧安装目录、代理、技能、工具、锁文件、请求、响应、总览或第五阶段输出：

- `套磁邮件/套磁信息.md`
- `套磁邮件/套磁模板.md`
- `套磁邮件/套磁跟进模板.md`
- `testdata/program/` 中阶段2至4的固定合成输入、两位教授各自的 `邮件输入.json` 和 `_contact_verify.json`

按以下命令复制，并排除旧总览、临时传递目录、本地状态、首封和跟进邮件：

```sh
PC68_INPUT_SOURCE="/private/tmp/pc68-task-20261009.U3yrne1G/run-Yo9u50JZ/consumer"
mkdir -p "$PC68_CONSUMER/套磁邮件" "$PC68_CONSUMER/testdata/program"
cp "$PC68_INPUT_SOURCE/套磁邮件/套磁信息.md" "$PC68_CONSUMER/套磁邮件/"
cp "$PC68_INPUT_SOURCE/套磁邮件/套磁模板.md" "$PC68_CONSUMER/套磁邮件/"
cp "$PC68_INPUT_SOURCE/套磁邮件/套磁跟进模板.md" "$PC68_CONSUMER/套磁邮件/"
rsync -a \
  --exclude '.tmp-stage5/' \
  --exclude '套磁邮件总览.md' \
  --exclude '套磁邮件状态.json' \
  --exclude '套磁邮件.md' \
  --exclude '套磁邮件.txt' \
  --exclude '套磁跟进邮件.md' \
  --exclude '套磁跟进邮件.txt' \
  "$PC68_INPUT_SOURCE/testdata/program/" "$PC68_CONSUMER/testdata/program/"
```

复制的 JSON 中含旧消费者绝对路径。只重定位这些字符串，并用新消费者中两个来源文件的实际路径和修改时间更新核验指纹：

```sh
set -eu
PC68_OLD_CONSUMER="$PC68_INPUT_SOURCE"
PC68_PROGRAM="$PC68_CONSUMER/testdata/program"
rg --files "$PC68_PROGRAM" -g '*.json' | while IFS= read -r file; do
  if ! jq --arg old "$PC68_OLD_CONSUMER" --arg new "$PC68_CONSUMER" \
      'walk(if type == "string" then (split($old) | join($new)) else . end)' \
      "$file" > "$PC68_RUN_ROOT/relocated.json"; then
    exit 1
  fi
  mv "$PC68_RUN_ROOT/relocated.json" "$file"
done

PC68_INFO_FP="$PC68_PROGRAM/info.json:$(stat -f %m "$PC68_PROGRAM/info.json")"
PC68_BOSHU_FP="$PC68_PROGRAM/boshu_analysis.json:$(stat -f %m "$PC68_PROGRAM/boshu_analysis.json")"
for file in \
  "$PC68_PROGRAM/教授研究/工学/山田太郎/_contact_verify.json" \
  "$PC68_PROGRAM/教授研究/社会情報/佐藤花子/_contact_verify.json"; do
  if ! jq --arg info "$PC68_INFO_FP" --arg boshu "$PC68_BOSHU_FP" \
      '.source_fingerprints.info_json = $info | .source_fingerprints.boshu_analysis = $boshu' \
      "$file" > "$PC68_RUN_ROOT/fingerprint.json"; then
    exit 1
  fi
  mv "$PC68_RUN_ROOT/fingerprint.json" "$file"
done

PC68_YAMADA_DIR="$PC68_PROGRAM/教授研究/工学/山田太郎"
PC68_SATO_DIR="$PC68_PROGRAM/教授研究/社会情報/佐藤花子"
jq -e --arg root "$PC68_PROGRAM" --arg dir "$PC68_YAMADA_DIR" \
  '.program_root == $root and .professor_dir == $dir and all(.emails[]; .professor_dir == $dir)' \
  "$PC68_YAMADA_DIR/邮件输入.json"
jq -e --arg root "$PC68_PROGRAM" --arg dir "$PC68_SATO_DIR" \
  '.program_root == $root and .professor_dir == $dir and all(.emails[]; .professor_dir == $dir)' \
  "$PC68_SATO_DIR/邮件输入.json"

rg --files "$PC68_PROGRAM" -g '*.json' | while IFS= read -r file; do
  if ! jq -e --arg old "$PC68_OLD_CONSUMER" \
      '[paths(scalars) as $path | getpath($path) | select(type == "string" and contains($old))] | length == 0' \
      "$file"; then
    exit 1
  fi
done

jq -e --arg info "$PC68_INFO_FP" --arg boshu "$PC68_BOSHU_FP" \
  '.source_fingerprints.info_json == $info and .source_fingerprints.boshu_analysis == $boshu' \
  "$PC68_YAMADA_DIR/_contact_verify.json"
jq -e --arg info "$PC68_INFO_FP" --arg boshu "$PC68_BOSHU_FP" \
  '.source_fingerprints.info_json == $info and .source_fingerprints.boshu_analysis == $boshu' \
  "$PC68_SATO_DIR/_contact_verify.json"
```

上述命令用 `jq` 确认两份 `邮件输入.json` 的 `program_root`、顶层 `professor_dir` 和每封邮件的 `professor_dir` 分别等于新消费者中的固定路径；再解析 `$PC68_PROGRAM` 下每个 JSON 的全部字符串值，确认旧消费者路径出现次数为0，并核对两份联系方式证据使用新来源指纹。这里仅迁移固定测试输入的位置，不重新生成或判断产品业务结果。

完成重定位后，只确认三份公共资料和两位教授的 `邮件输入.json`、`_contact_verify.json` 存在且可读，不重新运行阶段2、阶段3、阶段4、联系方式证据生成或两次 `stage5-plan`。若复用来源不存在、JSON 解析失败、路径核对失败或必需文件缺失，停止并把辛记为未执行；不得临场从零重建完整准备。

### 4.3 请求

正式输入为两位教授各一封邮件、`mode: both`：山田太郎使用邮件编号 `山田太郎::DIR00001::DIR00001_1`、`first_choice: true`、署名 `测试申请者甲`、方向 `地域交通规划`、日期 `2026-10-01`、邮箱 `taro@example.edu`；佐藤花子使用邮件编号 `佐藤花子::DIR00001::DIR00001_1`、`first_choice: false`、署名 `测试申请者乙`、方向 `沿岸防灾信息`、日期 `2026-10-02`、邮箱 `hanako@example.edu`。

用同一提交中的固定提示词和请求构建器生成 `request.json`：

```sh
PC68_PROGRAM="$PC68_CONSUMER/testdata/program"
uv run --no-project python \
  "$PC68_RECIPE_ROOT/.apm/skills/professor-contact/tests/runtime/build_issue68_eval_request.py" \
  --consumer-root "$PC68_CONSUMER" \
  --program-root "$PC68_PROGRAM" \
  --template-copy "$PC68_RUN_ROOT/prompt-template.txt" \
  --rendered-prompt "$PC68_RUN_ROOT/prompt.txt" \
  --hash-file "$PC68_RUN_ROOT/prompt.sha256" \
  --output "$PC68_RUN_ROOT/request.json" \
  > "$PC68_RUN_ROOT/request-build.json"
jq -r '.command' "$PC68_RUN_ROOT/request.json" | uv run --offline --no-project python -c 'import shlex, sys; argv = shlex.split(sys.stdin.read()); raise SystemExit(0 if "--ephemeral" not in argv else 1)'
```

只作这一次直接准备检查，不运行请求构建器6项单元测试。

取得明确正式请求授权后，在已经配置的评估服务仓库中执行以下命令一次：

```sh
direnv exec . sh -c 'curl -sS -X POST "http://127.0.0.1:${EVAL_PORT}/eval" -H "Content-Type: application/json" --data-binary @"$1"' sh "$PC68_RUN_ROOT/request.json" > "$PC68_RUN_ROOT/response.json"
```

不启动、停止或修改评估服务，不直接执行 `codex`，不追加模型、推理、并发或沙箱覆盖。

### 4.4 六个观察点

同一次请求只检查以下六项。先确认响应是 JSON 对象，再提取已有执行诊断；顶层执行信号只用于区分产品业务事实与环境或服务故障：

```sh
PC68_RESPONSE_OBJECT_OK=false
PC68_RESPONSE_DIAGNOSTICS_OK=false
PC68_RESPONSE_EVENTS_OK=false

if jq -e 'type == "object"' "$PC68_RUN_ROOT/response.json"; then
  PC68_RESPONSE_OBJECT_OK=true

  if jq '
    {passed: .passed,
     exit_code: .output.exit_code,
     termination_reason: .output.termination_reason,
     top_error: .error,
     output_error: .output.error,
     stderr: .output.stderr}
  ' "$PC68_RUN_ROOT/response.json" > "$PC68_RUN_ROOT/response-diagnostics.json"; then
    PC68_RESPONSE_DIAGNOSTICS_OK=true
  fi

  if jq -e '
    (.output | type == "object")
    and (.output.app_server_events | type == "array")
  ' "$PC68_RUN_ROOT/response.json"; then
    PC68_RESPONSE_EVENTS_OK=true
  fi
fi
```

上述三个 `jq` 都位于条件判断中，失败只保留对应的 `false` 状态，不受前文 `set -eu` 影响而提前退出。执行顺序固定为先执行第2项的两次目录检查，再处理所有事件依赖项；不能按编号先跑第1项。`PC68_RESPONSE_OBJECT_OK=false` 时，只把依赖响应的观察部分记为无法判断；`PC68_RESPONSE_DIAGNOSTICS_OK=true` 时，`.passed == false` 或非零 `exit_code` 仍只表示本次执行没有正常完成，不能单独判为产品业务失败：结合 `termination_reason`、已有错误字段和 `stderr`，运行服务、协议、支持性、就绪、容量、模型或访问故障记为无法判断。只有现有结构化业务结果、教授状态或业务文件给出具体产品合同失败事实时，才记为业务失败。只有 `PC68_RESPONSE_EVENTS_OK=true` 时才执行第1、3、4、5、6项中的事件命令；否则把这些部分记为无法判断，两位教授的业务文件仍已完成检查，也不得重发请求。

1. **两次教授委派与交接**。直接核对现有响应中的两次原生调用、根代理已有的两份单教授交接记录及各自业务结果，不检查子代理消息密文：

   ```sh
   jq -c '
     .output.app_server_events | to_entries[]
     | .key as $position
     | .value.message as $msg
     | select($msg.method == "rawResponseItem/completed")
     | $msg.params.item as $item
     | select($item.type == "function_call"
         and $item.namespace == "collaboration"
         and $item.name == "spawn_agent")
     | ($item.arguments | fromjson?) as $args
     | select($args.agent_type == "professor-contact-email-generator")
     | {position: $position, agent_type: $args.agent_type, task_name: $args.task_name}
   ' "$PC68_RUN_ROOT/response.json"
   ```

   两次的 `agent_type` 都须为 `professor-contact-email-generator`；直接对照已记录的 `owner_input_file` 创建结果与各教授输出，确认各自使用本地包、编号和选择，无混用。调用 `message` 加密或不可读不影响判定。未委派或实际串用为业务失败；必要业务事实无从观察时记为无法判断。

2. **两位教授结果使用同一个目录检查函数**。函数只接收教授目录，从该目录的 `邮件输入.json` 读取唯一 `email_id`，再检查四个业务文件和同目录状态行。它不接收教授姓名或预填邮件编号，避免两份复制脚本发生偏差：

   ```sh
   check_professor_outputs() {
     professor_dir="$1"
     email_pack="$professor_dir/邮件输入.json"
     state_file="$professor_dir/套磁邮件状态.json"

     email_id="$(jq -er '
       if ((.emails | type) == "array"
           and (.emails | length) == 1
           and ((.emails[0].email_id | type) == "string"))
       then .emails[0].email_id
       else empty
       end
     ' "$email_pack")" || return 1

     test -s "$professor_dir/套磁邮件.md" || return 1
     test -s "$professor_dir/套磁邮件.txt" || return 1
     test -s "$professor_dir/套磁跟进邮件.md" || return 1
     test -s "$professor_dir/套磁跟进邮件.txt" || return 1
     jq -e --arg id "$email_id" '
       (.emails | type == "object")
       and (.emails[$id] | type == "object")
       and ((.emails[$id].validation.result == "pass")
            or (.emails[$id].validation.result == "fail_after_2_rounds"))
       and (.emails[$id].followup | type == "object")
       and ((.emails[$id].followup.validation.result == "pass")
            or (.emails[$id].followup.validation.result == "fail_after_2_rounds"))
     ' "$state_file" >/dev/null
   }

   PC68_YAMADA_OUTPUT_CHECK=observed_failure
   if check_professor_outputs "$PC68_YAMADA_DIR"; then
     PC68_YAMADA_OUTPUT_CHECK=pass
   fi

   PC68_SATO_OUTPUT_CHECK=observed_failure
   if check_professor_outputs "$PC68_SATO_DIR"; then
     PC68_SATO_OUTPUT_CHECK=pass
   fi

   printf '%s\n' "山田太郎=$PC68_YAMADA_OUTPUT_CHECK" "佐藤花子=$PC68_SATO_OUTPUT_CHECK" \
     > "$PC68_RUN_ROOT/professor-output-checks.txt"
   ```

   两次调用都位于 `if` 条件中，一位失败不会让 `set -e` 提前退出，第二位仍会完成检查。随后分别人工核对山田与固定研究资料、选择、`2026-10-01`、`taro@example.edu` 对应，佐藤与固定研究资料、选择、`2026-10-02`、`hanako@example.edu` 对应。`fail_after_2_rounds` 表示审核已结束并记录问题，在第68号议题中可以通过；`pending`、`skipped`、缺行或缺文件仍不满足正常完成的结果。邮件风格及事实审查问题如实保留，不由本议题重新评分。只有本次要求的教授交接、隔离或产物归属错误才记业务失败；业务调用前的服务或环境故障记无法判断。

3. **两位教授结束后才重建总览**。直接对照本次已有的两位子代理结束事件与总览重建调用，不读取代理消息或证明完整内部调用链：

   ```sh
   jq -c '
     .output.app_server_events | to_entries[]
     | .key as $position
     | .value.message as $msg
     | $msg.params.item as $item
     | select(
         ($msg.method == "item/completed"
          and $item.type == "subAgentActivity" and $item.kind == "completed")
         or ($msg.method == "item/started" and $item.type == "commandExecution"
             and (($item.command // "") | contains("stage5-rebuild-overview"))))
     | {position: $position, agent_path: $item.agentPath, command: $item.command}
   ' "$PC68_RUN_ROOT/response.json"
   ```

   两位教授子代理均已结束、结果已交根代理，之后才启动一次总览则通过；提前或重复重建为业务失败，记录缺失导致无法辨认顺序时记无法判断。邮件审核 `pass` 和解密的代理消息均非条件。

4. **总览恰好一次且包含两位结果**。第3项已人工确认一次实际调用；这里直接核对派生文件：

   ```sh
   test -s "$PC68_PROGRAM/教授研究/套磁邮件总览.md"
   rg -F '山田太郎' "$PC68_PROGRAM/教授研究/套磁邮件总览.md"
   rg -F '佐藤花子' "$PC68_PROGRAM/教授研究/套磁邮件总览.md"
   ```

5. **本次临时交接清理**。直接用本次已有的临时交接路径及清理命令结果判断：根代理已删除本请求交接文件且清理命令成功则通过；已知文件仍存在则业务失败，记录无法确认时记无法判断。不建立额外路径清单、采集器或判定脚本，不扫描其他目录；教授的邮件及状态不属于清理范围。

6. **最终回复区分两位教授及总览结果**。从最后一条助手输出提取文本，再由人工按实际业务文件判断它是否分别说明山田、佐藤和总览结果；不要求固定措辞、原因码或完整对象：

   ```sh
   jq -r '
     [.output.app_server_events[]
       | select(.message.method == "rawResponseItem/completed")
       | .message.params.item
       | select(.type == "message" and .role == "assistant")
       | .content[]?
       | select(.type == "output_text")
       | .text]
     | last // empty
   ' "$PC68_RUN_ROOT/response.json" > "$PC68_RUN_ROOT/final-reply.txt"
   test -s "$PC68_RUN_ROOT/final-reply.txt"
   ```

每位教授只需检查代表业务结果的首封、跟进邮件和本地完成状态，不逐层重复核对 `files`、`choices`、`model_result`、`validation` 等内部字段。业务产物缺失、错归属或内容串用时按实际业务失败记录；因响应或明确字段缺失而无法观察时记为无法判断。

## 5. 停止、结果和交接

- 所有历史正式请求及失败记录保留原结果，不改写。2026-10-11 的既有运行和同次消费者补查已写入[执行记录](issue68-test-execution-2026-10-09.md)，本轮没有新发正式请求。后续正式请求须单独取得用户授权，不因邮件文案审核不通过而重复采样。
- 安装或准备阶段的外部错误由代理停止并报告，人工决定重试或结束。业务结果不满意不得重试。
- 结果只分通过、业务失败、无法判断和未执行。总览或清理失败单独记录，不覆盖已经成立的教授业务结果。
- 甲至庚复用历史7个证明方法内43个组件结果。辛仍检查原6项；邮件审核 `fail_after_2_rounds` 不阻断第68号测试，全部六项业务条件满足后交第三关口。
- 原正式失败、第六十版请求 #1 的执行记录、第五十五版至第五十八版审核记录、128项、6项和27项的运行记录均保留历史归属；它们不扩展本候选六个观察点或甲至庚的通过条件。

## 6. 当前状态

| 内容 | 状态 |
| --- | --- |
| 计划与版本 | 第六十二版，实际被测产品 `7472fd3688b11be199b333fda8caabdb00c7ff92`；[计划设计及第二关口审核通过](https://github.com/ScholarWorkflow/professor-contact/pull/72#issuecomment-6101070579)，业务目标和执行步骤未变 |
| 甲至庚 | 历史7个证明方法内43个组件继续复用，自动化重跑0项 |
| 辛 | 2026-10-11 同次正式运行与补查已记录：6项观察点均通过。两位教授各自首封和跟进文件存在、状态已写入、总览含双方结果、交接已清理；邮件审核均为 `fail_after_2_rounds`，不视为可发送稿 |
| 第三关口 | 此前[第三关口复核](https://github.com/ScholarWorkflow/professor-contact/pull/72#issuecomment-6101120351)所缺的同次目录检查、总览内容检查及锁定产品提交已在[执行记录](issue68-test-execution-2026-10-09.md)补齐；待第三关口审核者核定，不在此自行宣布通过 |

本次没有新增测试、重试、判定程序或采集材料。版本修订记录沿用版本历史及正式执行记录，不在本计划重复堆积。
