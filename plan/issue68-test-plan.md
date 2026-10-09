# 第68号议题测试计划：按最新规则精简

版本：`issue-68-test-plan-r56-2026-10-10`。

目标仓库：`ScholarWorkflow/professor-contact`；拉取请求：[第72号](https://github.com/ScholarWorkflow/professor-contact/pull/72)。本文件是唯一完整计划，取代第五十五版，不自行授予正式请求执行许可。

第五十五版按甲至辛写成8组，但交付材料实际引用了204个自动化测试方法：历史43项、五模块128项、请求构建器6项、调用约定27项；另安排1次正式业务运行。历史43项只复用，不是待执行测试；其余161项已有历史结果，但把完整套件继续列为当前验收依据违反“每个目标选择一个足够入口”“已有结果直接复用”和“不默认全仓回归”。第五十六版删除这些重复义务：**自动化测试重跑0项，只保留1次正式业务请求**。

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
| 辛：修复后的真实代理正常完成两位教授业务；`R68-4、R68-8、AD68-1、AD68-5` | 两位姓名不同的教授，各有一个有效本地包、完整选择和可区别的研究内容 | 两次准确教授委派；两位教授各自产出首封、跟进邮件和本地完成状态；总览最多重建一次并包含两位结果；本次临时传递目录被清理；最终回复准确区分两位教授及总览结果 | 发送1次普通第五阶段请求，只检查第4节六个观察点 |

辛保留一次真实运行，因为当前改动包含根代理和教授代理说明，历史确定性结果不能证明修复后的代理实际产生业务文件。该次运行不重复测试甲至庚的失败分支、阶段2至4、邮件渲染算法、校验算法或测试工具。

## 3. 复用结果与删除的重复义务

历史43项结果来自 [保留记录](../.apm/skills/professor-contact/tests/runtime/evidence/issue68-d1-r29-history.json)，对应 `P1` 至 `P7`，均为通过。第五十六版直接采用这些结果，不要求重新认证来源、重建夹具或重跑。

下列结果只作开发和持续集成历史，不属于本轮必测清单、第二关口或第三关口的通过条件，也不再运行：

- 五模块128项回归；其中包含阶段2至4、第59号、第64号、第65号、第67号等本轮范围外测试。
- 请求构建器6项单元测试；正式发送前直接解析实际 `request.json` 已足够，不再测试测试工具本身。
- `test_stage3_stage4_caller_contract.py` 的27项调用约定测试；其中绝大多数属于阶段3、阶段4和第67号议题。

既有运行记录继续保留原事实，不删除、不把历史失败改成通过，也不把上述161项写成当前验收数量。

## 4. 唯一待执行测试

### 4.1 产品、消费者和配置

1. 在第72号拉取请求分支当前干净工作树运行：

   ```sh
   git fetch origin codex/issue-68-stage5-per-professor
   test -z "$(git status --porcelain)"
   PC68_RECIPE_ROOT="$(pwd)"
   PC68_PRODUCT_SHA="$(git rev-parse HEAD)"
   test "$PC68_PRODUCT_SHA" = "$(git rev-parse FETCH_HEAD)"
   ```

   任一检查失败时停止。`git fetch` 网络错误由人工决定重试或结束，代理不自动重试。

2. 新建仓库外运行目录和干净消费者，按冻结提交正式安装：

   ```sh
   PC68_RUN_ROOT="$(mktemp -d /private/tmp/pc68-r56-20261010-XXXXXX)"
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

同一次请求只检查以下六项：

1. 响应已有事件中出现两次成功的 `spawn_agent`，两次 `agent_type` 均为 `professor-contact-email-generator`，分别对应山田太郎和佐藤花子。不配对完整调用链，不检查 `child_thread_reads`、父子关系字段、读取请求或任务元数据。
2. 山田太郎目录存在本次首封、跟进邮件和本地状态；内容与山田的固定研究资料、选择和邮箱对应。
3. 佐藤花子目录存在本次首封、跟进邮件和本地状态；内容与佐藤的固定研究资料、选择和邮箱对应。
4. 总览调用不超过一次；总览返回或总览文件包含两位教授本次结果。总览失败单独记录，不回滚教授结果。
5. 已知本次传递目录 `$PC68_CONSUMER/.tmp-stage5` 不存在。不搜索或证明其他内部路径。
6. 根代理最后回复准确区分两位教授的实际结果和总览结果，不要求固定措辞、原因码或完整对象。

每位教授只需检查代表业务结果的首封、跟进邮件和本地完成状态，不逐层重复核对 `files`、`choices`、`model_result`、`validation` 等内部字段。业务产物缺失、错归属或内容串用时按实际业务失败记录；因响应缺失而无法观察时记为无法判断。

## 5. 停止、结果和交接

- 正式请求只发送一次。请求是否已提交不明时暂停，不重发；先确认服务响应和业务文件。
- 安装或准备阶段的外部错误由代理停止并报告，人工决定重试或结束。业务结果不满意不得重试。
- 结果只分通过、业务失败、无法判断和未执行。总览或清理失败单独记录，不覆盖已经成立的教授业务结果。
- 甲至庚继续使用历史43项通过结果。辛只有六个观察点全部取得可判断结果且符合预期时才通过；随后交第三关口。
- 原正式失败、第五十五版审核记录、128项、6项和27项的运行记录保留历史归属，但不再作为第五十六版执行义务或通过条件。

## 6. 当前状态

| 内容 | 状态 |
| --- | --- |
| 当前计划 | 第五十六版；计划设计和第二关口均已通过；[设计复核](issue68-test-plan-r56-design-review.md)、[第二关口复核](issue68-test-plan-r56-gate2-review.md) |
| 实际规模 | 历史43项直接复用；自动化重跑0项；正式业务请求1次；六个观察点 |
| 甲至庚 | 历史结果继续有效，不重跑 |
| 辛 | 当前为无法判断；待一次正式正常业务请求 |
| 第三关口 | 尚未通过 |

第五十六版修订记录（2026-10-10）：验收决定人指出，按8个组名展示不能说明计划没有膨胀。重新按可执行方法计数后，当前交付材料共引用204个自动化测试方法，其中历史43项只应复用，128项、6项和27项属于重复回归、测试工具自证或范围外调用约定套件。第五十六版删除这161项当前验收义务，复用历史43项结果，只保留一次正式正常业务请求；同时删除阶段2至4重建、两次阶段5预检、完整子任务关系链及内部状态字段重复核对。第五十五版设计审核和第二关口因未发现这些违反测试规则的要求而失效。第五十六版计划设计和第二关口现已重新通过，正式请求仍须取得明确授权。
