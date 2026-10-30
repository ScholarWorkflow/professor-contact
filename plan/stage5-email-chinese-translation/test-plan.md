# Stage 5 邮件中文译文测试计划

- Test plan revision: TP1.2（仅补齐 T4 可执行 recipe；未执行）
- Requirement/implementation: [R1](implementation-plan.md)
- Baseline: `ad096fe31a4b5694cbe47a40f37b621435e1eeec`
- 独立 review：TP1 Gate 1 PASS；TP1.1 的 T3 Gate 2 已独立确认 PASS，T1–T2 Gate 2 沿用；TP1.2 的 T4 Gate 2 已独立复核 PASS，T4 Gate 3 仍未执行。来源见 [review-record.md](review-record.md)。执行结果：T1–T3 见 test-execution.md，T4 未执行；作者不自授 PASS。

## 必测清单（范围上限）
|目标|输入/场景|预期/检查入口|
|---|---|---|
|T1 双邮件正常渲染与发送隔离|现有合成教授 fixture，mode both，最终动态字段/choices，与两个 translation_source 对应中文 subject/body|当前 unittest 框架检查两个 md 正文后分别包含正确译文；两个 txt 精确等于各自 translation_source、无中文附节；模板字节不变；原日文长度/兴趣校验不把译文当输入。|
|T2 翻译失配/缺失拒绝和手改保护|同一 fixture 已生成输出后给出 stale source_text，及完整文件缺本次跟进行；合法译文输入遇现有手改 md|既有 CLI 返回明确失败/needs_decision，既有 md/txt/state 字节不变。只检查这三个实际改变/依赖的失败行为，不做类型/排列穷举。|
|T3 旧直接CLI兼容|现有 immutable 无 translations 调用|保持成功、模板固定文本不变、无译文；复用现有 `test_finalize_without_full_body_humanizer_preserves_fixed_segments`，同 case 增加 `assertNotIn("## 中文译文", md)`，显式确认省略参数时无译文节。|
|T4 模型生成译文忠实且 validator 边界正确|一次正常 Stage 5 mode both 小样例，已验证资料与选择，实际 generator 及 validator|查看首封/跟进最终 md/txt：中译完整覆盖最终 Subject+正文，否定/日期/事实/请求强度不变；无新事实；译文不发送；validator 不将中文计入日文长度/三句规则，不漏掉明显翻译缺陷。仅一次，不重跑上游业务。|

## Gate 2 可执行步骤
### T1–T3 云端离线
- 使用仓库现有 Python unittest 与 `.apm/skills/professor-contact/tests/test_stage5_immutable.py` 的 `BaseEnv/prepare/write_inputs/run_wrapper`，仅新增本功能用例；不新建测试框架或判定器。
- fixture 以 tempfile 创建独立 `/tmp` 状态，现有 contact-evidence stub 仅供离线 runner 检查，不声称真实外部服务/模型成功。不访问用户文件、Mac或生产配置。
- 在仓库根执行：`python -m unittest discover -s .apm/skills/professor-contact/tests -p 'test_stage5_email_translation.py' -v`（T1/T2）；T3 执行 `cd .apm/skills/professor-contact/tests && python -m unittest test_stage5_immutable.TestStage5ImmutableTemplates.test_finalize_without_full_body_humanizer_preserves_fixed_segments -v`。
- 日志放仓库外 `/tmp/stage5-email-translation-validation/`，记录产品 SHA/工作 diff、命令、exit/status/必要输出；不提交原始用户材料。
- 失败先保留输出并诊断；产品缺陷修复后仅重跑受影响项，不改变期望求通过，不跑全仓回归。

### T4 正式模型观察：单教授、首封+跟进、一次请求

**本次仅补步骤，未执行 T4。** TP1.2 不改变 T4 业务目标、R1 设计或 T1–T3 结果。下列准备/请求命令供后续获准执行者使用；不是本次文档维护授权下自动执行的命令。

#### A. 输入与版本（执行者填真实值，不猜历史目录）

```sh
# 两个路径必须由当前执行环境提供：
export PC155_RECIPE_ROOT='/实际/PR155检出目录'
export PC155_EVAL_ENV_ROOT='/实际/现有eval服务direnv目录'
# 可选：仅复用已经装好下列固定产品版本、与生产隔离的consumer；没有则留空。
export PC155_CONSUMER=''
export PC155_PRODUCT_SHA=bbd62bbae73ffe98e9f53b7ee986cc8080715c85
export PC155_RUN_ROOT="$(mktemp -d /tmp/pc155-t4-XXXXXX)"
```

`PC155_RECIPE_ROOT` 提供本计划及固定版本 fixture helper；它不是模型运行目录。合成数据由下面 C 中已存在的 `_stage5_issue59_test_support.py::write_issue59_stage5_fixture` 准备，不需要用户提供历史样例或编造业务数据。只选该 fixture 的一个教授/一个 email_id，mode both，不复用旧输出、不跑两教授矩阵。

固定 `bbd62bba...` 包含 PR155 全部产品及离线测试，后续纯计划提交无需重装；若产品变动，先更新固定版本和影响说明。当前未绑定的**精确环境缺口**只有：可访问的本 PR checkout、现有 eval 服务 direnv 根目录；可选已有隔离 consumer 路径（若需复用）。环境提供者给路径，不需要设计命令或准备业务资料。

准备前在执行环境确认 `python3`、`jq`、`yq`、`apm`、`direnv`、`curl` 可用，两必需目录可读；缺工具记准备阻塞，不自动安装工具/启动服务。consumer 必须在 producer/worktree 外，不是生产项目、不是源 checkout 的技能软链接视图。不得读取 eval 自身 trust list，不新增“预先信任证明”，不修改个人/global 安全配置。

#### B. 复用安装，必要时仅安装一次固定包

已有有效 consumer 则直接复用其安装，保留其原有配置；只核对 lock 中本产品的 resolved_commit。没有可复用安装才执行以下块一次，不把安装本身变成重复回归：

```sh
if [ -z "$PC155_CONSUMER" ]; then
  export PC155_CONSUMER="$PC155_RUN_ROOT/consumer"
  mkdir -p "$PC155_CONSUMER"
  (cd "$PC155_CONSUMER" && apm init -y --target codex &&
    apm install "https://github.com/ScholarWorkflow/professor-contact.git#$PC155_PRODUCT_SHA" \
      --target codex --trust-transitive-mcp)
fi
PC155_EXPECTED_SHA="$PC155_PRODUCT_SHA" yq -e \
  '.dependencies[] | select(.name == "professor-contact") | .resolved_commit == strenv(PC155_EXPECTED_SHA)' \
  "$PC155_CONSUMER/apm.lock.yaml"
```

APM 是仓库保留的既有正式安装路径（`README.md`、issue68 recipe）；此项不是 Nix 交付验证，不引入安装器变化。安装/lock检查失败即停，不临场用复制产品或软链接补偿。执行者检查本安装生成的项目配置中已有 exact named `professor-contact-email-generator` 和 `professor-contact-email-validator`；不通过 shell 调用另一个 Codex、复制角色指令或 inline 模拟子代理。已安装角色若实际调用失败，按 D/E 分类，不通过加安全配置绕过。

沿用现有隔离项目模型配置；若准备的是新 consumer，按既有 recipe 只将 `plan/issue68-eval-codex-config.toml` 的 `model=gpt-6-luna` 和 `model_reasoning_effort=low` 合入本 consumer 的 `.codex/config.toml`，保留其余安装内容：

```sh
yq eval-all -p toml -o toml '. as $item ireduce ({}; . * $item)' \
  "$PC155_CONSUMER/.codex/config.toml" \
  "$PC155_RECIPE_ROOT/plan/issue68-eval-codex-config.toml" > "$PC155_RUN_ROOT/config.toml"
cp "$PC155_RUN_ROOT/config.toml" "$PC155_CONSUMER/.codex/config.toml"
```

只在新 consumer 需要模型配置时使用该块；不读/改个人配置、不设 trust_level。请求参数明确指定 sandbox 和 cd；实际模型配置/角色加载失败据事实记环境问题，不将预先证明信任名单作为前置。

#### C. 用既有 fixture helper 准备单教授合成输入

每次用新的业务子目录，已有安装可复用。以下仅调用仓内现有 fixture 写入 helper，不运行 unittest 测试或 Stage 2–5 runner。helper 内为离线用例临时注册 checker，因此在准备结束的 `finally` 立刻 `doCleanups()`：撤销环境注入并删除临时 checker；正式模型进程只使用安装包的真实 contact-evidence checker。helper 写出的 schema-2 evidence 含实际源文件和非空指纹索引，是现有真实 checker 可消费的固定合成数据，不宣称上游真实论文核验通过。

```sh
export PC155_PROGRAM="$PC155_CONSUMER/testdata/$(basename "$PC155_RUN_ROOT")/program"
export PC155_MAIL_INPUT="$PC155_CONSUMER/testdata/$(basename "$PC155_RUN_ROOT")/套磁邮件"
python3 - <<'PYFIXTURE'
import importlib.util, json, os, sys, unittest
from pathlib import Path
recipe = Path(os.environ['PC155_RECIPE_ROOT']).resolve()
program = Path(os.environ['PC155_PROGRAM']).resolve()
consumer = Path(os.environ['PC155_CONSUMER']).resolve()
assert program.is_relative_to(consumer) and not program.exists()
assert not consumer.is_relative_to(recipe)
support = recipe / '.apm/skills/professor-contact/tests/_stage5_issue59_test_support.py'
spec = importlib.util.spec_from_file_location('pc155_fixture', support)
h = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = h
spec.loader.exec_module(h)
case = unittest.TestCase()  # 仅管理现有fixture的cleanup，不运行任何测试
try:
    fixture = h.write_issue59_stage5_fixture(program, case=case)
finally:
    case.doCleanups()  # 正式eval前删除checker stub并恢复环境
mail = Path(os.environ['PC155_MAIL_INPUT']); mail.mkdir(parents=True)
initial = mail/'套磁模板.md'; followup = mail/'套磁跟进模板.md'
initial.write_text("""{{大学}}／{{研究科}}／{{先生名}}先生
突然のご連絡失礼いたします。{{出身校}}出身の{{氏名}}と申します。
{{入学年度}}年{{入学月}}の{{専攻}}・{{学位}}への進学を検討しております。
{{兴趣段}}
{{未来志向}}
現在は{{学習中}}に取り組んでおります。
{{志望}}。
ご指導いただく可能性についてお伺いできますと幸いです。
お忙しいところ恐縮ですが、どうぞよろしくお願いいたします。
{{氏名}}
""",encoding='utf-8')
followup.write_text("""{{先生名}}先生
お世話になっております。{{出身校}}出身の{{氏名}}です。
{{初回送信日}}にお送りしたメールについて、再度ご連絡いたしました。
{{入学年度}}年{{入学月}}の{{大学}}・{{研究科}}の{{学位}}への進学を検討しており、{{研究主题}}に関心を持っております。
お忙しいところ恐縮ですが、ご検討いただけましたら幸いです。
どうぞよろしくお願いいたします。
{{氏名}}
連絡先：{{メールアドレス}}
""",encoding='utf-8')
choice = h.issue59_choices(fixture['email_ids'][0])
choice.update(initial_sent_date='2026-10-01',email_address=h.ISSUE59_EMAIL_ADDRESS)
owner = dict(program_root=str(program),email_pack=str(fixture['pack']),
             email_id=fixture['email_ids'][0],mode='both',
             template=str(initial),followup_template=str(followup),choices=choice)
handoff = program.parent/'owner-input.json'
handoff.write_text(json.dumps(owner,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
Path(os.environ['PC155_RUN_ROOT'],'fixture-paths.json').write_text(
    json.dumps(dict(owner_input=str(handoff),professor_dir=str(fixture['dirs'][h.ISSUE59_PROFESSOR]),
                    email_id=fixture['email_ids'][0]),ensure_ascii=False,indent=2)+'\n')
print(handoff)
PYFIXTURE
export PC155_OWNER_INPUT="$(dirname "$PC155_PROGRAM")/owner-input.json"
```

模板是本测试的明确合成用户输入，不修改任何用户模板；译文、result JSON、来源表与validator结论均不预填。fixture 的鲜度/缓存由既有准备器生成，不在正式拒绝后更新时间戳求通过。正式初始 plan 若仍返回上游或资料门禁，保留实际结果并记 fixture/环境无法判断，不能改门禁或扩为上游采集。这不影响已完成 T1–T3。

#### D. 一次真实模型请求

只给普通业务信息和 exact named generator 入口，不在测试提示词重复翻译实现步骤或代写产品规则。generator 按已安装自身规则完成 initial plan、生成、中文翻译、finalize，并调用真实 named validator；不请求绕过输入门禁。把下面请求构造命令保留原样，业务数据从 handoff JSON 读取，不人工抄教授路径：

```sh
python3 - <<'PY'
import json, os, shlex
from pathlib import Path
run = Path(os.environ['PC155_RUN_ROOT'])
prompt = ('请调用已安装的 professor-contact-email-generator 原生具名子代理，'
          '处理这个单教授 Stage 5 业务输入文件：'+os.environ['PC155_OWNER_INPUT']+
          '。按工作流完成首封与无回复跟进邮件及最终校验，返回实际结果。')
(run/'prompt.txt').write_text(prompt+'\n')
argv = ['--json','--skip-git-repo-check','--sandbox','workspace-write',
        '--cd',os.environ['PC155_CONSUMER'],'--',prompt]
(run/'request.json').write_text(json.dumps({'command':shlex.join(argv),'timeout':900},
                                         ensure_ascii=False,indent=2)+'\n')
PY
# 现有eval服务接收codex exec参数；本shell不执行codex、不启动服务。
pc155_request_rc=0
direnv exec "$PC155_EVAL_ENV_ROOT" sh -c \
  'test -n "$EVAL_PORT" || exit 2; curl --connect-timeout 10 --max-time 930 -sS \
   -X POST "http://127.0.0.1:${EVAL_PORT}/eval" -H "Content-Type: application/json" \
   --data-binary @"$1" -o "$2" -w "%{http_code}\n"' sh \
  "$PC155_RUN_ROOT/request.json" "$PC155_RUN_ROOT/response.json" \
  > "$PC155_RUN_ROOT/http-status.txt" 2> "$PC155_RUN_ROOT/request.stderr" || pc155_request_rc=$?
printf '%s\n' "$pc155_request_rc" > "$PC155_RUN_ROOT/request-exit.txt"
```

只发送一次；timeout、网络中断或不确定服务是否继续时不自动重发，保留同一请求及现有输出后人工决定。没有预先读取 trust list 或测试角色能力的 eval。读取JSON响应的实际执行状态（如 `passed`、`exit_code`、`termination_reason`，具体以响应存在字段为准）与最终业务结果；HTTP 200 / passed true 单独不等于翻译通过。按需查看已有 response 中 generator/validator 结果确认真实调用，不新增全事件来源认证、跟踪器或裁判。

#### E. 输出与人工判定（同次结果，不加模型轮次）

- 输出在 `$PC155_PROGRAM/教授研究/X分野/試験 教授/`。以该次返回的 output_id/files 和 `套磁邮件状态.json` 中本 email 的 initial/followup 文件映射为准，不猜带方向后缀文件名；读取对应两份 md/txt，保留 `$PC155_RUN_ROOT/{request.json,response.json,http-status.txt,request-exit.txt,request.stderr}`。不上传原始私密配置或令牌。
- 人工逐份对照 md 的最终 `## 邮件正文` Subject+正文与紧随其后的中文译文：主题、称呼、各段、日期、数字、署名完整对应；否定、可能性、不确定性与请求强度不变；无新增经历/论文事实。首封与跟进分别核对，不看生成前旧稿。txt 只有相同日文 Subject+正文、没有中文译文节，模板保持原文。
- 读取该次真实 validator verdict/issues：中文不得被计入日文长度、三句兴趣或标题逐字规则。若译文有明显漏译/错译，人工记录业务失败并核对 validator 是否漏报；**不人为注入额外坏译文再跑一轮**，正常译文没有缺陷时不虚称已验证所有拒绝分支。
- 环境/准备无法判断：缺consumer安装依赖、fixture准备失败、eval服务，真实 named调用 machine-level失败，源核验阻塞或请求无完整结果；记录具体缺口，不改安全设置/模板/门禁求通过。
- 业务失败：请求确实完成但漏译、新事实、译文进入txt、validator误将中文判作日文违规，或实际generator跳过既有必需validator。保留产物，交产品owner修复；不自行换方法/提高模型/重复采样。
- 通过：本次两封实际最终产物满足上述T4目标，且具名validator完成；仍由独立 reviewer给T4 Gate3，执行者只记录事实。首次运行足够，不新增双harness、安装回归或完整上游流程。

方法依据：本仓 `plan/issue68-test-plan.md §4.1` 的 APM固定安装、`_stage5_issue59_test_support.py` 的既有单教授fixture准备、`plan/issue-81-test-plan.md` 的现有 `/eval` 请求形状；这里只取本目标所需部分。明确**不继承**历史信任override/预先授权证明、两教授委派矩阵、来源过程认证和额外采样要求。当前未获得具体执行环境位置时 T4保持未执行；recipe本身已完整，变量是环境绑定而非缺少操作设计。

## 记录与结束
结果分通过/业务失败/无法判断/未执行；T1–T3 离线机械结果不能替代 T4 翻译语义及实际模型接线。未完成 T4 不宣称整体通过或可合并。仅更新本目录简短执行记录；独立 reviewer 给正式 Gate 结论。
