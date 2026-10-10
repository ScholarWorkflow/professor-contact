# 第68号议题测试计划：按最新规则精简

版本：`issue-68-test-plan-r58-2026-10-10`。

目标仓库：`ScholarWorkflow/professor-contact`；拉取请求：[第72号](https://github.com/ScholarWorkflow/professor-contact/pull/72)。本文件是唯一完整计划，取代第五十七版，不自行授予正式请求执行许可。

第五十五版按甲至辛写成8组，交付材料引用了三批自动化结果：历史 `P1` 至 `P7` 的7个证明方法、方法内43个组件结果；五模块128项；请求构建器6项；另有调用约定27项和1次正式业务运行。后面三批共161项不再作为本轮通过条件。第五十八版保持**自动化测试重跑0项，只执行1次正式业务请求**，同时补上历史证据到当前产品基线的逐组影响判断，并把两位教授的产物检查收敛为一个只接收教授目录的公共函数。

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
| 辛：修复后的真实代理正常完成两位教授业务；`R68-4、R68-8、AD68-1、AD68-5` | 两位姓名不同的教授，各有一个有效本地包、完整选择和可区别的研究内容 | 当前安装源码明确要求单教授沿用同一顺序；本次请求有两次准确教授委派；两位教授各自产出首封、跟进邮件和本地完成状态；总览最多重建一次并包含两位结果；本次实际记录的临时传递路径被清理；最终回复准确区分两位教授及总览结果 | 发送1次普通第五阶段请求，并按第4节命令检查六个观察点 |

辛保留一次真实运行，因为当前改动包含根代理和教授代理说明，历史确定性结果不能证明修复后的代理实际产生业务文件。该次运行不重复测试甲至庚的失败分支、阶段2至4、邮件渲染算法、校验算法或测试工具。

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

`35f2785` 到参考产品基线还新增了阶段1至4的教授本地事务处理，并重构了上述共享目录约束；这些变化没有改变 `P1` 至 `P7` 已覆盖输入的阶段5结果。`72f2084` 之后到参考产品基线，阶段5核心脚本没有可执行逻辑变化；唯一产品文件变化是教授代理对缺少 `--email-pack` 时行为的说明修正。该说明属于真实代理编排，交由本次辛的正式业务请求直接观察，不用旧确定性结果替代。

拉取请求头可以继续增加计划和审核记录，不要求提交号等于 `6169c87`。正式执行前只比较下列五个产品文件与参考基线的内容；完全相同时继续复用7个历史证明，任一文件不同时停止并更新受影响证明的判断：教授代理、根技能、流程说明、`contact_state.py`、`stage5_immutable.py`。

下列结果只作开发和持续集成历史，不属于本轮必测清单、第二关口或第三关口的通过条件，也不再运行：

- 五模块128项回归；其中包含阶段2至4、第59号、第64号、第65号、第67号等本轮范围外测试。
- 请求构建器6项单元测试；正式发送前直接解析实际 `request.json` 已足够，不再测试测试工具本身。
- `test_stage3_stage4_caller_contract.py` 的27项调用约定测试；其中绝大多数属于阶段3、阶段4和第67号议题。

既有运行记录继续保留原事实，不删除、不把历史失败改成通过，也不把43个组件写成43个测试方法，或把上述161项写成当前验收数量。

## 4. 唯一待执行测试

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
     .apm/agents/professor-contact-email-generator.agent.md \
     .apm/skills/professor-contact/SKILL.md \
     .apm/skills/professor-contact/docs/workflow-reference.md \
     .apm/skills/professor-contact/scripts/contact_state.py \
     .apm/skills/professor-contact/scripts/stage5_immutable.py
   ```

   任一检查失败时停止。`git fetch` 网络错误由人工决定重试或结束，代理不自动重试。

2. 新建仓库外运行目录和干净消费者，按冻结提交正式安装：

   ```sh
   PC68_RUN_ROOT="$(mktemp -d /private/tmp/pc68-r58-20261010-XXXXXX)"
   PC68_CONSUMER="$PC68_RUN_ROOT/consumer"
   mkdir -p "$PC68_CONSUMER"
   cd "$PC68_CONSUMER"
   apm init -y --target codex
   apm install "https://github.com/ScholarWorkflow/professor-contact.git#$PC68_PRODUCT_SHA" --target codex --trust-transitive-mcp
   yq -e --arg sha "$PC68_PRODUCT_SHA" '.dependencies[] | select(.name == "professor-contact") | .resolved_commit == $sha' apm.lock.yaml
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
    and ((.output.thread_id | type) == "string" and (.output.thread_id | length) > 0)
    and ((.output.turn_id | type) == "string" and (.output.turn_id | length) > 0)
    and (((.output.runtime_generation | type) == "number")
         or ((.output.runtime_generation | type) == "string"
             and (.output.runtime_generation | length) > 0))
  ' "$PC68_RUN_ROOT/response.json"; then
    PC68_RESPONSE_EVENTS_OK=true
  fi
fi
```

上述三个 `jq` 都位于条件判断中，失败只保留对应的 `false` 状态，不受前文 `set -eu` 影响而提前退出。执行顺序固定为先执行第2项的两次目录检查，再处理所有事件依赖项；不能按编号先跑第1项。`PC68_RESPONSE_OBJECT_OK=false` 时，只把依赖响应的观察部分记为无法判断；`PC68_RESPONSE_DIAGNOSTICS_OK=true` 时，`.passed == false` 或非零 `exit_code` 仍只表示本次执行没有正常完成，不能单独判为产品业务失败：结合 `termination_reason`、已有错误字段和 `stderr`，运行服务、协议、支持性、就绪、容量、模型或访问故障记为无法判断。只有现有结构化业务结果、教授状态或业务文件给出具体产品合同失败事实时，才记为业务失败。只有 `PC68_RESPONSE_EVENTS_OK=true` 时才执行第1、3、4、5、6项中的事件命令；否则把这些部分记为无法判断，两位教授的业务文件仍已完成检查，也不得重发请求。

1. **根代理顺序与两次教授委派**。先在本次安装的当前源码中定位顺序合同，由人工按上下文确认两份文件均写明“发现与确定选择 → 按教授构建本地传递 → 调用并等待该教授代理 → 全部结束后至多重建一次总览”，且单教授采用同一顺序。这是一次窄范围静态检查，不运行第二次正式请求，也不恢复27项调用约定套件：

   ```sh
   rg -n -B 2 -A 2 '单教授请求.*同一顺序|单教授请求采用相同顺序' \
     "$PC68_CONSUMER/.agents/skills/professor-contact/SKILL.md" \
     "$PC68_CONSUMER/.agents/skills/professor-contact/docs/workflow-reference.md"
   ```

   再给结构化事件保留数组位置和 `runtime_seq`，并按 `call_id` 配对两次 `spawn_agent` 调用与返回：

   ```sh
   PC68_ROOT_THREAD="$(jq -er '.output.thread_id' "$PC68_RUN_ROOT/response.json")"
   PC68_TURN_ID="$(jq -er '.output.turn_id' "$PC68_RUN_ROOT/response.json")"
   PC68_RUNTIME_GENERATION="$(jq -ce '.output.runtime_generation' "$PC68_RUN_ROOT/response.json")"

   jq '
     [.output.app_server_events | to_entries[]
       | {event_index: .key,
          runtime_seq: .value.runtime_seq,
          runtime_generation: .value.runtime_generation,
          method: .value.message.method,
          thread_id: .value.message.params.threadId,
          turn_id: .value.message.params.turnId,
          item: .value.message.params.item}]
   ' "$PC68_RUN_ROOT/response.json" > "$PC68_RUN_ROOT/event-ledger.json"

   jq --arg root "$PC68_ROOT_THREAD" --arg turn "$PC68_TURN_ID" \
      --argjson generation "$PC68_RUNTIME_GENERATION" '
     [.[]
       | select(.runtime_generation == $generation
           and .thread_id == $root
           and .turn_id == $turn
           and .method == "rawResponseItem/completed"
           and .item.type == "function_call"
           and .item.namespace == "collaboration"
           and .item.name == "spawn_agent")
       | {event_index, runtime_seq, runtime_generation, thread_id, turn_id,
          call_id: .item.call_id,
          arguments: (.item.arguments | fromjson)}] as $calls
     | [.[]
       | select(.runtime_generation == $generation
           and .thread_id == $root
           and .turn_id == $turn
           and .method == "rawResponseItem/completed"
           and .item.type == "function_call_output")
       | {event_index, runtime_seq, call_id: .item.call_id,
          result: (.item.output | fromjson?)}] as $outputs
     | [$calls[] as $call
       | {event_index: $call.event_index,
          runtime_seq: $call.runtime_seq,
          runtime_generation: $call.runtime_generation,
          thread_id: $call.thread_id,
          turn_id: $call.turn_id,
          call_id: $call.call_id,
          arguments: $call.arguments,
          result_event_index: ([$outputs[] | select(.call_id == $call.call_id) | .event_index] | first),
          result: ([$outputs[] | select(.call_id == $call.call_id) | .result] | first)}]
   ' "$PC68_RUN_ROOT/event-ledger.json" > "$PC68_RUN_ROOT/spawn-check.json"

   jq -e '
     length == 2
     and ([.[].arguments.task_name] | unique | length == 2)
     and all(.[].arguments; .agent_type == "professor-contact-email-generator")
     and all(.[];
       (.event_index | type == "number")
       and (.result_event_index | type == "number")
       and .result_event_index > .event_index)
     and all(.[].result; (.agent_id | type == "string") and (.agent_id | length > 0))
   ' "$PC68_RUN_ROOT/spawn-check.json"
   ```

   **单教授交接的证明**不靠任务名猜测。对 `spawn-check.json` 的两行分别查看 `arguments.message`，再回到同一运行代、根线程和当前轮次中该调用之前创建或读取交接文件的完成事件。调用消息必须指向同一个绝对 `owner_input_file`；完成事件必须成功并直接给出该文件实际解析后的 JSON 对象，而不只是创建命令或提示词意图。用对象确认教授目录等于山田或佐藤之一，两个调用的文件路径不同，且对象内所有 `professor_dir` 和选择行都只属于这一位教授。执行记录分别写下调用事件和对象完成事件的 `event_index`，再写 `call_id/agent_id/professor_dir/owner_input_file` 并引用原事件，不另建交接判定器或证据账本。交接对象出现第二位教授目录或原始多教授选择对象时记为业务失败；结构化事件不能把调用、完成事件与实际解析对象唯一关联时记为无法判断。这样证明的是两次根线程当前轮次调用各自收到一个单教授对象，而不是仅证明调用了两个同类型任务。

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
       and .emails[$id].validation.result == "pass"
       and (.emails[$id].followup | type == "object")
       and .emails[$id].followup.validation.result == "pass"
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

   两次调用都位于 `if` 条件中，一位失败不会让 `set -e` 提前退出，第二位仍会完成检查。随后分别人工核对山田与固定研究资料、选择、`2026-10-01`、`taro@example.edu` 对应，佐藤与固定研究资料、选择、`2026-10-02`、`hanako@example.edu` 对应。`pending`、`fail_after_2_rounds`、`skipped`、缺行或缺字段均不能通过。若文件缺失且响应诊断明确显示业务调用前的服务或环境故障，记为无法判断；已有文件内容或状态明确违反合同，记为业务失败。

3. **证明根代理先消费两位结果，再生成总览**。使用三段结构化证据：`subAgentActivity` 给出的子线程与 `agentPath` 关联；根线程当前轮次收到的 `agent_message`，其 `recipient` 为 `/root`，正文是该 `agentPath` 的 `FINAL_ANSWER` 且顶层载荷含对应 `professor_dir/status/reason_code`；同一根线程、当前轮次的 `stage5-rebuild-overview` `commandExecution` 开始事件。先断言同一运行代内的总览开始事件恰好一次，再显示该运行代、根线程和当前轮次的三类原事件：

   ```sh
   jq -e --arg root "$PC68_ROOT_THREAD" --arg turn "$PC68_TURN_ID" \
      --argjson generation "$PC68_RUNTIME_GENERATION" '
     [.[]
       | select(.runtime_generation == $generation
           and .thread_id == $root
           and .turn_id == $turn
           and .method == "item/started"
           and .item.type == "commandExecution"
           and ((.item.command // "") | contains("stage5-rebuild-overview")))]
     | length == 1
   ' "$PC68_RUN_ROOT/event-ledger.json"

   jq -c --arg root "$PC68_ROOT_THREAD" --arg turn "$PC68_TURN_ID" \
      --argjson generation "$PC68_RUNTIME_GENERATION" '
     .[]
     | select(.runtime_generation == $generation
         and .thread_id == $root
         and .turn_id == $turn)
     | select(.item.type == "subAgentActivity"
         or (.method == "rawResponseItem/completed"
             and .item.type == "agent_message"
             and .item.recipient == "/root")
         or (.method == "item/started"
             and .item.type == "commandExecution"
             and ((.item.command // "") | contains("stage5-rebuild-overview"))))
     | {event_index, runtime_seq, method, thread_id, turn_id, item}
   ' "$PC68_RUN_ROOT/event-ledger.json"
   ```

   人工用同一运行代内的 `subAgentActivity` 把每个子线程关联到唯一 `agentPath`，再把两条当前轮次回执分别关联到山田、佐藤；在执行记录中写下两条回执和唯一总览开始事件的 `event_index`、`runtime_seq` 与总览调用标识。通过条件是：两位教授各有且只有一条可归属的消费回执，唯一总览开始值严格大于两条回执值中的较大者。该数值关系直接证明总览在两位结果被根代理消费之后才开始，而对全部开始事件计数证明本轮总览只调用一次。子代理自己的完成消息、`wait` 状态文字或最终回复中的教授名字都不能替代消费回执。事件缺少唯一关联、回执正文不满足上述形状，或同一运行代内 `runtime_seq` 不严格递增时记为无法判断。

4. **总览恰好一次且包含两位结果**。第3项已要求一次可排序的实际调用；这里直接核对派生文件：

   ```sh
   test -s "$PC68_PROGRAM/教授研究/套磁邮件总览.md"
   rg -F '山田太郎' "$PC68_PROGRAM/教授研究/套磁邮件总览.md"
   rg -F '佐藤花子' "$PC68_PROGRAM/教授研究/套磁邮件总览.md"
   ```

5. **仅核对本次实际记录的临时传递路径已经清理**。先用 `jq` 提取本次响应中根代理的工具调用字段；人工只从这些调用中记录为本次两位教授传递而创建、写入或传给子代理的绝对临时路径，写成 JSON 字符串数组 `$PC68_RUN_ROOT/observed-transfer-paths.json`。不得填入业务产物路径，不得搜索消费者或其他目录补路径，也不得假定目录名是 `.tmp-stage5`：

   ```sh
   jq '
     [.output.app_server_events[]
       | select(.message.method == "rawResponseItem/completed")
       | .message.params.item
       | select(.type == "custom_tool_call" and .name == "exec")
       | {call_id, input}]
   ' "$PC68_RUN_ROOT/response.json" > "$PC68_RUN_ROOT/current-request-exec-calls.json"

   jq -e '
     type == "array"
     and length > 0
     and all(.[]; type == "string" and startswith("/"))
   ' "$PC68_RUN_ROOT/observed-transfer-paths.json"

   jq -r '.[]' "$PC68_RUN_ROOT/observed-transfer-paths.json" |
     while IFS= read -r path; do
       test ! -e "$path" || exit 1
     done
   ```

   若结构化事件未记录可识别的本次传递路径，或无法把传递路径与业务产物路径区分，本观察点记为无法判断；空数组不能通过。若识别出路径但仍存在，记为业务失败。这样只检查已有证据，不证明或搜索任何未暴露的内部路径。

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

- 正式请求只发送一次。请求是否已提交不明时暂停，不重发；先确认服务响应和业务文件。
- 安装或准备阶段的外部错误由代理停止并报告，人工决定重试或结束。业务结果不满意不得重试。
- 结果只分通过、业务失败、无法判断和未执行。总览或清理失败单独记录，不覆盖已经成立的教授业务结果。
- 甲至庚继续使用历史7个证明方法内43个组件的通过结果；复用依据是第3节逐组影响判断。辛只有六个观察点全部取得可判断结果且符合预期时才通过；随后交第三关口。
- 原正式失败、第五十五版至第五十七版审核记录、128项、6项和27项的运行记录保留历史归属，但不作为第五十八版执行义务或通过条件。

## 6. 当前状态

| 内容 | 状态 |
| --- | --- |
| 当前计划 | 第五十八版；设计和第二关口均已通过；[设计复核](issue68-test-plan-r58-design-review.md)、[第二关口复核](issue68-test-plan-r58-gate2-review.md) |
| 实际规模 | 历史7个证明方法内43个组件按影响判断复用；自动化重跑0项；正式业务请求1次；六个观察点 |
| 甲至庚 | 历史结果继续有效，不重跑 |
| 辛 | 当前为无法判断；待一次正式正常业务请求 |
| 第三关口 | 尚未通过 |

第五十七版修订记录（2026-10-10）：保留第五十六版删除161项重复义务的决定，继续复用历史43项结果且只安排一次正式正常业务请求。补充当前安装源码中的单教授同序静态合同检查，不新增第二次请求；把清理检查从固定 `$PC68_CONSUMER/.tmp-stage5` 改为结构化事件中本次请求实际记录的传递路径，未记录或无法区分时明确记为无法判断；并为六个观察点补上直接命令。该候选曾通过计划设计和第二关口；本次限定修订的结论以新的复核记录为准。正式请求仍须取得明确授权。

第五十七版限定修订（2026-10-10）：状态文件检查改为对两位教授各自的本次目标行要求首封和跟进 `validation.result` 均为 `pass`，明确排除失败、待处理、跳过和未完成状态。该候选当时采用的顶层失败分类已由下一段执行分类限定修订取代。未改变必测清单、请求次数、重试规则或历史结果复用范围。

第五十七版执行分类限定修订（2026-10-10）：不再把 `.passed == false` 或非零 `exit_code` 单独等同于产品业务失败；使用已有 `termination_reason`、错误字段、`stderr` 和已产生的教授业务文件判断。环境或服务故障记为无法判断，只有具体产品业务失败事实才记为业务失败；顶层执行失败不阻止分别检查已经落盘的教授结果。未增加日志、测试、重试、调用链或来源证明；本项计划设计限定复核和第二关口限定复核均已通过。

第五十七版响应控制流限定修订（2026-10-10）：响应对象、诊断提取和事件数组解析全部放入明确条件分支，解析失败只设置可用状态，不因 `set -eu` 提前退出；两位教授的文件与状态检查始终在条件块之外先执行。未改变结果分类、观察点、请求次数或重试规则；本项计划设计限定复核和第二关口限定复核均已通过。

第五十八版修订（2026-10-10）：把历史证据准确表述为7个证明方法内43个组件，并补上从生产提交 `35f2785` 到产品基线 `6169c87` 的 `P1` 至 `P7` 影响判断；两位教授的产物与状态检查合并为同一个只接收教授目录的函数，两次调用分别保存结果，一位失败不会阻止另一位；单教授交接必须关联实际交接对象并证明只含一个教授目录；根代理消费以当前轮次 `agent_message` 回执为证据，总览 `commandExecution` 的开始 `runtime_seq` 必须大于两条消费回执。未增加正式请求、自动化重跑或重复回归。
