# 兴趣段字数不计论文标题 — 测试计划 TP2

- Requirement revision: R1；关联执行计划：同目录 `execution-plan.md` EP1。
- Plan revision: TP2（2026-10-28）。只修订 T1 的生成规则检查方式和执行步骤；第 1 节必测清单、T1–T4 的业务预期及 EP1 已批准的产品要求保持不变。
- Baseline: `b67dd3ca4d29dfc78f57988564b219c71b582674`（产品基线）；测试资产准备基线：`b36ed0613cbe5eeae950acdc4e8195ec0218537d`。目标产品实现版本：待实现。
- Review status: 第二关待复核；第三关未执行。本轮修订不自行授予 PASS，准备期试跑和自动 CI 均不作为第三关结果。

## 1. 唯一必测清单

| 项 | 目标及输入 | 预期结果 | 足够的检查入口 |
| --- | --- | --- | --- |
| T1 | 合法三部分结果，②完整逐字引用当前邮件包的长标题，净正文 ≤180、含标题总长 >200；复用合法 source_map 等现有夹具 | 正式入口接受并输出完整标题及原正文，固定模板不因计数变化；生成给模型的规则明确标题文本免计、外侧符号计数 | 扩展现有 `test_stage5_immutable.py` 的 plan/render 场景，经 wrapper 的 stage5-plan 与 stage5-finalize；断言实际结果和最终文本，不调用真实模型 |
| T2 | 相同有效标题引用，净正文字符数分别 180、181、200、201；将外围书名号/标点计入预先构造的正文长度 | 180 无长度警告；181、200 仅长度警告；201 硬拒绝。警告/拒绝数字为净正文长度 | 现有测试框架直接调用共享 `validate_email_raw(email, raw)`；不在多个层重复边界证明 |
| T3 | 在原本正常的三部分中放入长的任意引号内容或不在当前包内的标题文本，使按原口径正文 >200；另保留一个仅供共享 validator 计数检查的无标题结构合法输入（不代表符合完整邮件②要求） | 非可信标题文本不得得到免计，仍因长度拒绝；无标题输入在共享 validator 的计数检查中维持原行为，不豁免完整邮件②要求 | 同一 validator 测试；不要求新增完整标题语义判定器或大量拼写/Unicode 组合 |
| T4 | 采用 201 净正文的结果尝试 finalize，目标目录已有邮件；静态阅读改动涉及的正文规则 | 拒绝且原邮件不变；三部分、② 1–3 篇/标题真实、③与未来志向、source_map 规则未被放宽，全部相关文档用同一计数口径 | 将既有 immutable 拒绝不重写测试模式用于该长度失败；其余未变规则以 diff 与契约人工核对，不重复业务回归 |

本清单来自 R1 直接改变的接受、警告、拒绝和输出保留行为。标题完整逐字匹配、不重复扣同一跨度按 EP1 静态核对，不另加组合穷举。已有适用通过结果直接引用；普通自动 CI 不扩大本清单。

## 2. 执行步骤（TP2 修订；正式测试未执行）

沿用仓库 `.apm/skills/professor-contact/tests/test_stage5_immutable.py` 的 `unittest`、`BaseEnv` 临时目录、`prepare`/`raw_result`、`run_wrapper`，不新增设施、安装路径、网络或模型调用。生产文件、用户目录和实际邮件不得用于测试。复用可用 Python 环境，不为此重装 Nix/APM 或建立干净消费者。

### 2.1 已准备的资产

- 新模块：`.apm/skills/professor-contact/tests/test_stage5_interest_title_length.py`，单类 `TestStage5InterestTitleLength`，5 个 selector（T1 接受一个、T2 一个含 4 个 `subTest`、T3 两个、T4 一个）；T1 生成规则由 §2.4 的一次人工观察完成，不重复写成自动判定。原 `test_t1_generated_rule_states_the_title_exemption` 及其词表、正则、相邻字符窗口检查已按 TP2 从测试模块移除；`COUNT_WORDS`、`CLAUSE_SPLIT`、`TITLE_EXEMPTION`、`EXEMPTION_TITLE`、`INSIDE_TITLE`、`SCOPED_SYMBOL`、`SYMBOL_EXEMPTION`、`EXEMPTION_SYMBOL`、`SYMBOL_PAREN_EXEMPTION`、`_PAREN_SYMBOL` 与 `_clauses`/`title_exemptions`/`symbol_exemptions` 一并删除，模块不再含自然语言判定器。
- 分片登记：`plan/test-grouping/shards.json` 的 shard3 已加入 `{"name": "test_stage5_interest_title_length", "stage": "stage5"}`；测试代码对齐后该模块只收集上述 5 个确定性 selector，自动 CI 不再运行已废止的规则检查，其结果与 TP2 的 T1-规则判定无关。
- 夹具复用：通过 `test_stage5_immutable` 的模块对象取 `helpers`/`BaseEnv`/`parse`/`run_wrapper`，再由 `helpers.TestStage5` 取 `prepare`/`raw_result`/`choices`，因此不重新收集 immutable 模块的既有用例（该模块当前实际收集 13 个；`shards.json` 的旧记录写 10 个，属既有漂移，本 PR 不改），也不新增夹具文件。`setUp` 只把 `AAAA1111` 的标题换成 80 字符的 `Synthetic comparison of input patterns across heterogeneous processing pipelines`，其余论文、gap、sidecar、verify 缓存、模板均由既有夹具生成。
- 准备基线：`b36ed0613cbe5eeae950acdc4e8195ec0218537d`（本 PR 当前 head，产品尚未改动）；解释器 `/run/current-system/sw/bin/python3`（3.14.7）。

### 2.2 计数语料

模块内 `interest_corpus(title, net)` 生成三段，使「去掉该标题后的长度」恰为 `net`：

- ① `HEAD` + 中性填充；② `先生のご論文「<title>」を拝読し、比較の可能性に気づかされました。`，标题在其中逐字出现且整段只出现一次；③ `例えば、…` + 中性填充。
- 书名号 `「」`、`先生のご論文`、`を拝読し、`、句读点等外围字符全部保留计数，只有标题本身免计。
- 标题 80 字符时：`net` 180/181/200/201 对应三段总长 260/261/280/281。因此「含标题总长 >200 而净正文 ≤180」这一条件在 T1 成立。
- 填充只用固定的中性日文串，不含方法名、指标、数据集、年份，避免与既有排除清单冲突。

### 2.3 环境

从 PR worktree 根目录执行；产物只落在仓库外的独立目录，测试自身写入 `BaseEnv` 的临时目录。

```bash
checkout=$(git rev-parse --show-toplevel)
run_dir=$(mktemp -d /tmp/interest-title-length.XXXXXX)
export TMPDIR="$run_dir"
cd "$checkout/.apm/skills/professor-contact/tests"
git rev-parse HEAD > "$run_dir/target-version.txt"
/run/current-system/sw/bin/python3 --version > "$run_dir/python-version.txt" 2>&1
```

`TMPDIR` 指向 `run_dir` 后，`BaseEnv` 的 `tempfile.TemporaryDirectory()` 与全部临时邮件文件都在该目录下，teardown 会删除。准备阶段使用固定目录 `/tmp/interest-title-length-prep.20261028` 存放日志，正式执行改用上面的 `mktemp`。

### 2.4 逐项命令与预期观察

在 §2.3 的同一个 shell 中执行 T1–T4 的确定性检查，另对 T1 生成规则只观察一次。每项分别保存退出码，单项失败不阻断其他项。不运行旧的 `test_t1_generated_rule_states_the_title_exemption`：它通过专用词表和正则近似判断自然语言，能误放行“标点忽略”或完全不提外围符号的规则，也可能误拒绝等义正确措辞。

**T1-接受**（长标题不占限额、保留原文和模板）：

```bash
/run/current-system/sw/bin/python3 -m unittest -v \
  test_stage5_interest_title_length.TestStage5InterestTitleLength.test_t1_long_cited_title_is_accepted_and_rendered_verbatim \
  > "$run_dir/t1.log" 2>&1; printf '%s\n' "$?" > "$run_dir/t1.exit"
```

**T1-生成规则**（单次直接观察；使用同一既有夹具和正式 wrapper，不新增自然语言判定器）：

```bash
/run/current-system/sw/bin/python3 - <<'PY' > "$run_dir/t1-rule.txt" 2> "$run_dir/t1-rule.err"
from test_stage5_interest_title_length import TestStage5InterestTitleLength, parse, run_wrapper

case = TestStage5InterestTitleLength(
    "test_t1_long_cited_title_is_accepted_and_rendered_verbatim")
case.setUp()
try:
    case.prepare()
    out = run_wrapper(
        "stage5-plan", "--program-root", case.root,
        "--email-pack", case.email_pack)
    if out.returncode != 0:
        raise RuntimeError(f"stage5-plan failed: {out.returncode}: {out.stdout} {out.stderr}")
    print(parse(out)["jobs"][0]["model_input"]["rules"]["interest"])
finally:
    case.tearDown()
PY
printf '%s\n' "$?" > "$run_dir/t1-rule.exit"
```

执行者直接阅读 `$run_dir/t1-rule.txt` 中完整的 `rules.interest` 原文，记录该项是否同时明确表达：

1. 兴趣段仍为三部分，并保留原 180 字符软限制；
2. 当前邮件包中实际完整逐字引用的论文标题文本免计；
3. 标题外的书名号、引号、标点和其他正文字符继续计数，且没有相矛盾的文字。

三项中有缺失或冲突，就记 **T1-规则业务失败**；提取命令失败、未得到该字段，记 **无法判断**。人工检查不限制同义措辞、关键词间隔或括号写法。`t1-rule.exit=0` 仅证明取得了文本，**不等于规则通过**。只记录是否满足上述三项及必要的原文片段，不进行第二次规则检查。

**T2**（净正文 180／181／200／201 四个边界）：

```bash
/run/current-system/sw/bin/python3 -m unittest -v \
  test_stage5_interest_title_length.TestStage5InterestTitleLength.test_t2_net_body_thresholds_are_180_181_200_201 \
  > "$run_dir/t2.log" 2>&1; printf '%s\n' "$?" > "$run_dir/t2.exit"
```

**T3**（包外标题不免计；无可信标题保持原口径）：

```bash
/run/current-system/sw/bin/python3 -m unittest -v \
  test_stage5_interest_title_length.TestStage5InterestTitleLength.test_t3_foreign_quoted_title_is_not_exempt \
  test_stage5_interest_title_length.TestStage5InterestTitleLength.test_t3_pack_without_titles_keeps_the_original_counting \
  > "$run_dir/t3.log" 2>&1; printf '%s\n' "$?" > "$run_dir/t3.exit"
```

**T4**（净 201 字符拒绝，原有邮件不被覆盖）：

```bash
/run/current-system/sw/bin/python3 -m unittest -v \
  test_stage5_interest_title_length.TestStage5InterestTitleLength.test_t4_over_cap_finalize_is_rejected_without_rewriting_existing_email \
  > "$run_dir/t4.log" 2>&1; printf '%s\n' "$?" > "$run_dir/t4.exit"
```

逐项预期：

- **T1-接受**：`validate_email_raw` 对净 180、含 80 字符标题总长 260 的三段返回空列表；`stage5-finalize` 返回 `status=ok`；`套磁邮件.txt` 包含按换行拼接的三段原文、完整标题及 `FIXED-BEGIN`、`FIXED-SELFINTRO`、`FIXED-INTEREST`、`FIXED-FUTURE`、`FIXED-LEARNING`、`FIXED-END` 六个固定标记；`套磁邮件.md` 同样含完整标题。
- **T1-生成规则**：按照上面的三项观察点人工给出通过／业务失败／无法判断；无自动正则判定。
- **T2**：`INTEREST_SOFT_CAP`／`INTEREST_HARD_CAP` 仍为 180／200。净 180 无长度问题；净 181、200 均恰好一条以 `WARNING` 开头的长度问题；净 201 恰好一条不以 `WARNING` 开头的长度问题。181／200／201 的提示数字包含相应净长度。
- **T3-包外标题**：把当前邮件包没有的标题形文本放入第②部分，净正文 201、总长 289；应有一条硬拒绝，显示总长 289，不豁免任意引号内容。
- **T3-无标题包**：移除测试邮件包的 `papers` 后仍用同样语料，总长 260；共享 validator 计数检查应硬拒绝并报告 260。此输入只用于核对计数，不声称满足整封邮件的标题引用要求。
- **T4**：先以净 100（总长 180）成功 finalize，保存 `套磁邮件.md`、`套磁邮件.txt`、`套磁邮件状态.json` 三份文件字节；再以净 201 finalize，应退出非零、返回 `status=error`、`reason_code=invalid_result_json`、提示含 201，且这三份文件均不变化。

### 2.5 T4 的人工静态核对

长度断言之外，T4 只静态核对未放宽的产品约束与相关文档同步。产品实现落地后读取相应 diff 并记录结论；生成规则原文已由 §2.4 T1-生成规则检查，本节不再重复。准备阶段这些文件仍是旧口径，不得据此声称已核对：

| 核对点 | 路径 | 观察要求 |
| --- | --- | --- |
| 三部分结构、② 1–3 篇与标题真实、③ 与未来志向、source_map | `scripts/_stage5_email.py` 的 `validate_email_raw` | 除长度计算外无新增/放宽/删除判定；`source_map ④ is retired`、③ 只锚 `anchorable_gaps` 等既有分支保留 |
| 计数只免标题、外围符号仍计 | 同上 `validate_email_raw` 的长度段 | 豁免来源只取 `email["papers"][].title` 的非空字符串；同一跨度不重复扣除；正文未被改写 |
| 阈值与警告/错误通道 | `scripts/contact_state.py` 的 `INTEREST_SOFT_CAP`/`INTEREST_HARD_CAP` | 仍为 180/200；warning 仍走 `WARNING` 前缀被 plan/finalize 过滤，硬拒绝仍走 `invalid_result_json` |
| 契约文档 | `SKILL.md` 第 348 行、`docs/stage5-legacy-contract.md` 第 55/218/301 行 | 三处字数表述与 runner 一致；218 行「恰 3 个非空兴趣段字段」等结构约束未被改写 |
| 校验 agent 口径 | `.apm/agents/professor-contact-email-validator.agent.md` Rule 3 与计数相关表述 | 仍要求标题与 `papers[].title` 逐字一致；如提及字数，与新口径一致 |
| generator 冲突 | `.apm/agents/professor-contact-email-generator.agent.md` 第 44 行起引用 `docs/stage5-legacy-contract.md` 的段落 | 无与新口径矛盾的旧表述；不因口径同步而放宽真实标题要求 |

### 2.6 失败处理

- 自动断言失败或 T1 生成规则人工观察不满足预期，记对应业务失败；提取结果缺失或命令无法执行时记无法判断。`t1-rule.exit=0` 不单独构成 T1-规则通过。
- 保留首次 `$run_dir` 输出，不放宽预期、不换输入求通过。
- 缺少依赖、解释器或夹具记「无法判断」，停止受影响项，继续可独立项；同一输入最多按一次明确的环境修正重试一次，并保留首次输出。
- 方法或配置确需调整时，先修订本文件对应步骤并记录原因，再由执行者重跑受影响项；无关项不重跑。
- 无外部服务依赖，不设真实模型重采样，不做全仓回归。

### 2.7 有限预检记录

以下属于 TP1 准备期历史记录，保留原事实，不构成 TP2 检查、第二关批准或第三关正式结果。旧 T1-规则 selector 的词表结论自 TP2 起不再引用：

- `py_compile` 通过；`unittest` 收集到 6 个 selector（1 个类，无 immutable 模块的既有用例混入；该模块当前收集 13 个）。
- `python scripts/check_test_shards.py` 报 `OK: 85 test modules across 4 shards, each with a stage`；`--print shard3` 列出 `test_stage5_interest_title_length`。
- 夹具冒烟：既有 `TestStage5.prepare` 能把 80 字符标题写进 `邮件输入.json` 的 `papers[0].title`（实测 `TITLE_LEN 80`），`source_map`/`allowed_sources`/`anchorable_gaps` 与 `validate_email_raw` 的既有要求全部满足（旧口径下三段 142 字符返回空 problem）。
- 语料自检：`interest_corpus` 在 180/181/200/201 四档下「总长 − 标题长度」分别等于目标值（260/261/280/281 − 80），且标题在三段中只出现一次。
- 写入路径冒烟：T4 的第一步用同一标题、净 100（总长 180）的结果 finalize，退出码 0 且三份文件均已生成，说明该夹具能提交一封逐字引用长标题的邮件、保护字符串校验不会因标题变长而误报；T4 的失败点确实落在长度拒绝之后的断言上。
- 为确认失败原因做过一次试跑（不是结果，也不是第三关）：6 个 selector 报 7 个 failure，全部是产品缺失——T1-接受与 T2 净 180 报 `interest total 260 exceeds hard cap 200`（净 180 应无 problem）；T1-规则报旧规则文本不含免计措辞；T2 的 181 报 `interest total 261`（无 181）、200 报硬拒绝（应为 WARNING）、201 报 `interest total 281`（无 201）；T4 的 `message` 是 `interest total 281 exceeds hard cap 200`（无 201）。T3 两个 selector 在基线上通过，属保持行为项，不构成 R1 证据。日志留在 `/tmp/interest-title-length-prep.20261028`。
- 该试跑属于准备期越界：它调用了必测清单里的正式 selector 和 `stage5-finalize` 入口，超出本角色「不执行正式用例」的边界。此处如实披露，不据此声称任何结果或关口状态；第二关前不再调用目标命令，第三关仍须由执行者按本 recipe 首次正式执行。
- 仍缺的输入：产品侧标题免计计数与 `model_input.rules.interest` 新口径尚未实现，因此 T1/T2/T4 在准备基线上按产品缺失失败是预期结果。下一负责人：本地执行工程师。
- 提交后自动 CI（PR #150，shard3）与上述预期一致：`Ran 286 tests`，7 个 failure，全部来自本模块且原因相同——T1-接受与 T2 净 180 报 `interest total 260 exceeds hard cap 200`；T1-规则为旧规则措辞；T2 的 181 报 261、200 报硬拒绝、201 报 281；T4 的 `message` 报 281。T3 两个 selector 为 `ok`。这与准备期试跑的 7 个 failure 逐项相同，属产品缺失，不是测试资产缺陷；登记 shard 后该分片在产品落地前会保持红灯，见 §4 的 R2。
- TP2 对齐后的自动 CI（提交 `ea34be6`，shard3）：`Ran 285 tests`，6 个 failure，全部是本模块的计数断言——T1-接受与 T2 净 180 报 `interest total 260`，T2 的 181 报 261、200 报硬拒绝、201 报 281，T4 的 `message` 报 281；T3 两个 selector 仍为 `ok`，已废止的规则 selector 不再出现在运行列表里。失败数由 7 降到 6，减少的正是被 TP2 废止的那一项，其余与上一轮逐项相同，仍属产品缺失。该分片在产品落地前保持红灯。

## 3. 证据与状态

不增加真实模型 eval、全教授流程、全仓回归、重复安装、来源认证、自建判定器或完整运行轨迹。生成规则是否使用新口径以 model_input/契约核对，确定性计数以现有框架断言；不是文风质量测试。

- 第一关（必测清单）：通过，见同目录 `review.md`。该记录里的 TP1 SHA-256 `6348e4da…` 对应 recipe 补齐前的版本；本文件 §1 逐字未改（该节内容 SHA-256 `473f1323…`），因此第一关结论继续适用，补齐 recipe 不重开第一关。
- 第二关（具体步骤）：TP2 已改为 5 个确定性 selector 加一次规则原文人工观察；测试模块已按 TP2 对齐，旧规则 selector 及其词表／正则／窗口判定已删除，模块现只收集 5 个 selector。第二关待独立审核，本计划不自行声明通过；TP1 的准备审核记录见 §4，不能代替 TP2 结论。
- 第三关（正式结果）：未执行；产品实现尚未交付，T1/T2/T4 当前按产品缺失失败。
- 下一负责人：测试计划审核者复核受影响的第二关步骤；产品实现工程师落实 R1，执行工程师按 TP2 正式执行，结果审核者核对结果。

依据：[Test Engineer Rule](https://app.notion.com/p/3d80101a85f380d8a8f5ce528141e253) 与 [PROJECT_CONSENSUS](https://app.notion.com/p/3d60101a85f3815a8c43f271f2b4d91d)。仅复核受影响项；文档 SHA 改变本身不触发重跑。

## 4. 测试准备符合性审核记录（TP1 历史记录）

本节仅保留旧候选的准备审核与冻结事实；其中 T1 词表、正则及窗口条件的冻结不再适用于 TP2。TP2 的现行检查方法以 §2.4 为准；原审核结论不自动扩展到本次修订。

按 [实现符合性审核入口](https://github.com/ScholarWorkflow/professor-contact) 调用独立 `implementation_reviewer`，对本角色应交付的三项产物（测试模块、shard 登记、本文件 §2 recipe）做只读核对。共 7 轮：前 6 轮为「部分完成」，逐轮指出 T1-规则文本匹配的假失败与假通过（子句共现过严、符号否定子串、括号边界两侧、敬体与复合动词词表、括号内免计标题 vs 符号等），均由本角色修正并交同一入口定向复核。

**第 7 轮结论：完整。** 审核确认：T1–T4 均有对应 selector 与可执行 recipe；断言读取真实可观测量（`validate_email_raw` 返回、wrapper 退出码与 payload、最终文件字节），无自我验证、无跳过、无清单外新增测试项；产品代码与产品文档零改动；§3 未声称任何关口通过或第三关已执行。审核时版本：测试模块 `ebdd8fe3bb4caa3ba8fd08e1db32ea3e700044c0c836e9ab6b58ea954ac690ef`、本文件 `e2a229c935fd7e5b47d381f6f3a8f9ca9fcb357bca9b9d46fda104047731302f`、`shards.json` `4a8039461bacbefec49d24116969f3b4f939781c2dd34ad9f4c4d1e7145429aa`。

**冻结**：T1-规则的文本匹配判定自该版起冻结，不再增加词表或窗口条件。后续若产品 `rules.interest` 的落地文本与判定不兼容，按 Test Engineer Rule 先修本计划再改断言，不在执行阶段临场放宽。§2.4 已写明该判定的已知覆盖边界（`标点忽略` 一类词表外措辞、间隔大于 10 字符、跨子句 `均不计`、完全不提符号的规则），这些属已声明范围，不作为缺陷。

**未解除、按归属移交**：
- R2 待计划负责人：EP1 §1「本 PR 只提交计划和必要审核记录」与本轮已批准准备测试代码、以及 shard3 在产品缺失时 CI 红灯之间的不一致，需计划负责人统一 EP1 范围与落地/CI 预期。本角色不修改 EP1。
- T1 措辞待测试计划工程师：§1 T1「外侧符号计数」目前只有反向证据（「没把符号一起免掉」），完全不提符号的规则会通过。是否收窄 §1 措辞由测试计划工程师裁定；本角色不改必测清单。

本结论仅表示本角色准备产物已落实有效计划，不代表第二关、第三关或合并批准。


## 5. TP2 修订说明（2026-10-28）

- **修订依据**：Test Engineer Rule 第 2 节要求每项目标采用一个足够的检查入口；第 3 节允许人工判断业务目标，并在现有断言或直接观察足够时禁止新增专用判定器。本次不更改第 1 节必测清单，已通过的第一关继续有效。
- **本轮修正**：T1-生成规则只从正式 `stage5-plan` 输出读取 `model_input.rules.interest` 一次，按已批准的“标题免计、外围符号计数”要求直接人工判断。废止基于关键词、固定字符间隔和括号规则的自动近似判定，也不在 T4 静态核对中重复检验同一生成规则。
- **实际文件状态**：TP2 修订本身只改测试计划；测试代码对齐随后由本地测试工程师完成——已删除 `test_t1_generated_rule_states_the_title_exemption` 及其词表、正则、相邻字符窗口判定（含 `COUNT_WORDS`、`CLAUSE_SPLIT`、`TITLE_EXEMPTION`、`EXEMPTION_TITLE`、`INSIDE_TITLE`、`SCOPED_SYMBOL`、`SYMBOL_EXEMPTION`、`EXEMPTION_SYMBOL`、`SYMBOL_PAREN_EXEMPTION`、`_PAREN_SYMBOL` 与 `_clauses`/`title_exemptions`/`symbol_exemptions`），模块现只收集 5 个确定性 selector，自动 CI 不再运行该规则检查。
- **范围与风险**：T1–T4 的输入、接受／警告／拒绝、正文原样保留以及失败不覆盖现有邮件的目标不变；不增加真实模型运行、全流程回归或新的证明材料。此前“外侧符号计数”只有反向词表检查、可能误放行未说明符号的规则；现通过人工直接核对原文解决。TP1 的历史预检与旧版审核记录不被重写。
- **未完成项**：第二关等待按 TP2 复核；产品标题免计实现未提交；第三关未执行。测试代码已对齐 TP2。仅修改计划与测试代码不代表测试已通过或 PR 可以合并。
