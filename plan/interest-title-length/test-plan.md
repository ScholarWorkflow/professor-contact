# 兴趣段字数不计论文标题 — 测试计划 TP1

- Requirement revision: R1；关联执行计划：同目录 `execution-plan.md` EP1。
- Baseline: `b67dd3ca4d29dfc78f57988564b219c71b582674`（产品基线）；测试资产准备基线：`b36ed0613cbe5eeae950acdc4e8195ec0218537d`。目标产品实现版本：待实现。
- Proposed review status: pending。本文为必测清单与方法候选；正式执行全部 **未执行**，无 PASS 声明。

## 1. 唯一必测清单

| 项 | 目标及输入 | 预期结果 | 足够的检查入口 |
| --- | --- | --- | --- |
| T1 | 合法三部分结果，②完整逐字引用当前邮件包的长标题，净正文 ≤180、含标题总长 >200；复用合法 source_map 等现有夹具 | 正式入口接受并输出完整标题及原正文，固定模板不因计数变化；生成给模型的规则明确标题文本免计、外侧符号计数 | 扩展现有 `test_stage5_immutable.py` 的 plan/render 场景，经 wrapper 的 stage5-plan 与 stage5-finalize；断言实际结果和最终文本，不调用真实模型 |
| T2 | 相同有效标题引用，净正文字符数分别 180、181、200、201；将外围书名号/标点计入预先构造的正文长度 | 180 无长度警告；181、200 仅长度警告；201 硬拒绝。警告/拒绝数字为净正文长度 | 现有测试框架直接调用共享 `validate_email_raw(email, raw)`；不在多个层重复边界证明 |
| T3 | 在原本正常的三部分中放入长的任意引号内容或不在当前包内的标题文本，使按原口径正文 >200；另保留一个仅供共享 validator 计数检查的无标题结构合法输入（不代表符合完整邮件②要求） | 非可信标题文本不得得到免计，仍因长度拒绝；无标题输入在共享 validator 的计数检查中维持原行为，不豁免完整邮件②要求 | 同一 validator 测试；不要求新增完整标题语义判定器或大量拼写/Unicode 组合 |
| T4 | 采用 201 净正文的结果尝试 finalize，目标目录已有邮件；静态阅读改动涉及的正文规则 | 拒绝且原邮件不变；三部分、② 1–3 篇/标题真实、③与未来志向、source_map 规则未被放宽，全部相关文档用同一计数口径 | 将既有 immutable 拒绝不重写测试模式用于该长度失败；其余未变规则以 diff 与契约人工核对，不重复业务回归 |

本清单来自 R1 直接改变的接受、警告、拒绝和输出保留行为。标题完整逐字匹配、不重复扣同一跨度按 EP1 静态核对，不另加组合穷举。已有适用通过结果直接引用；普通自动 CI 不扩大本清单。

## 2. 执行 recipe（已准备，未执行）

沿用仓库 `.apm/skills/professor-contact/tests/test_stage5_immutable.py` 的 `unittest`、`BaseEnv` 临时目录、`prepare`/`raw_result`、`run_wrapper`，不新增设施、安装路径、网络或模型调用。生产文件、用户目录和实际邮件不得用于测试。复用可用 Python 环境，不为此重装 Nix/APM 或建立干净消费者。

### 2.1 已准备的资产

- 新模块：`.apm/skills/professor-contact/tests/test_stage5_interest_title_length.py`，单类 `TestStage5InterestTitleLength`，6 个 selector（T1 两个、T2 一个含 4 个 `subTest`、T3 两个、T4 一个）。selector 全名见 2.4，不另建索引。
- 分片登记：`plan/test-grouping/shards.json` 的 shard3 增加 `{"name": "test_stage5_interest_title_length", "stage": "stage5"}`；`python scripts/check_test_shards.py` 报 `OK: 85 test modules across 4 shards, each with a stage`，`--print shard3` 含该模块。
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

以下四个代码块在 2.3 的同一个 shell 里依次执行，`$run_dir` 与 `$TMPDIR` 沿用到最后；每项单独记录退出码，单项失败不阻断其余项。

`T1`（接受 + 完整标题与原文保留 + 生成规则口径），预计 10–25 s：

```bash
/run/current-system/sw/bin/python3 -m unittest -v \
  test_stage5_interest_title_length.TestStage5InterestTitleLength.test_t1_long_cited_title_is_accepted_and_rendered_verbatim \
  test_stage5_interest_title_length.TestStage5InterestTitleLength.test_t1_generated_rule_states_the_title_exemption \
  > "$run_dir/t1.log" 2>&1; printf '%s\n' "$?" > "$run_dir/t1.exit"
```

`T2`（净正文 180/181/200/201 四边界），预计 10–25 s：

```bash
/run/current-system/sw/bin/python3 -m unittest -v \
  test_stage5_interest_title_length.TestStage5InterestTitleLength.test_t2_net_body_thresholds_are_180_181_200_201 \
  > "$run_dir/t2.log" 2>&1; printf '%s\n' "$?" > "$run_dir/t2.exit"
```

`T3`（非包内标题不免计；无标题包维持原口径），预计 5–15 s：

```bash
/run/current-system/sw/bin/python3 -m unittest -v \
  test_stage5_interest_title_length.TestStage5InterestTitleLength.test_t3_foreign_quoted_title_is_not_exempt \
  test_stage5_interest_title_length.TestStage5InterestTitleLength.test_t3_pack_without_titles_keeps_the_original_counting \
  > "$run_dir/t3.log" 2>&1; printf '%s\n' "$?" > "$run_dir/t3.exit"
```

`T4`（201 净正文 finalize 拒绝且既有邮件不变），预计 10–25 s：

```bash
/run/current-system/sw/bin/python3 -m unittest -v \
  test_stage5_interest_title_length.TestStage5InterestTitleLength.test_t4_over_cap_finalize_is_rejected_without_rewriting_existing_email \
  > "$run_dir/t4.log" 2>&1; printf '%s\n' "$?" > "$run_dir/t4.exit"
```

逐项预期：

- **T1-接受**：`validate_email_raw` 对净 180、含标题总长 260 的三段返回空列表；`stage5-finalize` 返回 `status=ok`；`套磁邮件.txt` 含三段原文（以换行连接）与 80 字符标题，固定标记 `FIXED-BEGIN`/`FIXED-SELFINTRO`/`FIXED-INTEREST`/`FIXED-FUTURE`/`FIXED-LEARNING`/`FIXED-END` 六个仍在（与既有 immutable 测试一致）；`套磁邮件.md` 同样含标题。断言读实际文件与退出码，不调用真实模型。
- **T1-规则**：`stage5-plan` 的 `jobs[0].model_input.rules.interest` 同时满足三件事。①字数口径仍在：规则文本含 `180`/`字数`/`文字数`/`总长` 之一。②标题免计：某个子句（按 `；;。` 与换行切分）内，标题词（`标题`/`タイトル`/`題名`）与免计词（`不计入`/`不计`/`免计`/`不算`/`不纳入`/`不计算`/`不参与`/`不占用`/`不列入`/`排除`/`免除`/`除外`/`不含`/`以外`/`対象外`/`含めない`/`含まない`/`数えない`/`除く`/`カウントしない`/`計上しない`/`計上いたしません`）在 30 个字符内相邻成立，正反两种语序都算；免计词紧前 10 字符出现 `标题内`/`标题中`/`标题里`/`标题の内` 时，视为在排除标题内部的东西（如 `标题内方法名除外`），该次匹配不算。③外围符号不得被免计：同一个子句里符号词（`书名号`/`引号`/`标点`/`符号`/`括弧`/`括号`/`記号`/`句読点`/`「」`）与免计词在 10 字符内相邻即判为与 R1 冲突。相邻判定查三种形态：符号在前、免计词在前（`不计书名号与标点`）、以及符号后接括号再在括号内免计（`书名号与标点（均不计）`）；前两种的间隔不跨括号，所以「标题免计」写在括号里、符号照常计数写在括号外的排版不会被误判。第三种只在括号内免计的是符号时才判冲突：括号内出现标题词、且该标题词之后不再出现符号词时（`书名号与标点照常计数（论文标题不计）`、`（论文标题除外）`），说明括注解释的是标题，跳过；若标题词之后又提到符号（`（含标题与标点，均不计）`、`（标题与标点都不计）`），免计范围仍含符号，判冲突。若该符号词被 `内`/`中`/`里`/`以内`/`以外`/`之外`/`の内`/`の外` 限定（如 `书名号内的论文标题不计`、`书名号以外的字符照常计数`），说明限定的是符号范围而不是把符号免计，该次匹配跳过；限定判定取符号词两侧各约 10–12 字符的窗口。③ 只做反向检查，不要求出现「照常计数」一类正面措辞——自然语言正面表达太多，穷举词表只会造成假失败；因此不提符号的规则也会通过，这是本判据已知的覆盖边界。这是对生成规则文本的近似核对，不是语义解析器：只确认规则有没有写出该口径、有没有把符号一起免掉，不认证措辞质量。②③可以落在不同子句。
- **T2**：`INTEREST_SOFT_CAP`/`INTEREST_HARD_CAP` 仍为 180/200。净 180 → 无 problem；净 181、200 → 恰好 1 条 problem 且以 `WARNING` 开头；净 201 → 恰好 1 条且不以 `WARNING` 开头。181/200/201 三例还要求 problem 文本中的数字包含净长度；旧口径只报含标题的总长 261/280/281，因此这三例会按产品缺失失败。
- **T3-非包内标题**：把一段 88 字符、邮件包从未出现的标题形文本逐字放进 ②，净正文 201、总长 289；期望恰好 1 条非 `WARNING` problem，数字为总长 289，证明豁免只认本邮件包实际标题，不认任意引号内容。
- **T3-无标题包**：深拷贝邮件包并移除 `papers`，用 T1 同一语料（净 180、总长 260）；期望恰好 1 条非 `WARNING` problem、数字 260，证明没有可信标题时计数不变。该输入只用于共享 validator 的计数检查，不代表符合完整邮件②要求。
- **T4**：先用同一标题、净 100（总长 180）的结果成功 finalize 一次，记录 `套磁邮件.md`/`套磁邮件.txt`/`套磁邮件状态.json` 三份字节；再用净 201 结果 finalize，期望退出码非 0、payload `status=error`、`reason_code=invalid_result_json`、`message` 含 `201`（旧口径只报总长 281），三份文件字节与记录完全一致。

### 2.5 T4 的人工静态核对

长度断言之外，T4 还要求「未放宽的规则」与「全部相关文档同一计数口径」。产品实现落地后按下列路径逐条读 diff 并记录观察结论（准备阶段这些文件仍是旧口径，不得据此声称已核对）：

| 核对点 | 路径 | 观察要求 |
| --- | --- | --- |
| 三部分结构、② 1–3 篇与标题真实、③ 与未来志向、source_map | `scripts/_stage5_email.py` 的 `validate_email_raw` | 除长度计算外无新增/放宽/删除判定；`source_map ④ is retired`、③ 只锚 `anchorable_gaps` 等既有分支保留 |
| 计数只免标题、外围符号仍计 | 同上 `validate_email_raw` 的长度段 | 豁免来源只取 `email["papers"][].title` 的非空字符串；同一跨度不重复扣除；正文未被改写 |
| 阈值与警告/错误通道 | `scripts/contact_state.py` 的 `INTEREST_SOFT_CAP`/`INTEREST_HARD_CAP` | 仍为 180/200；warning 仍走 `WARNING` 前缀被 plan/finalize 过滤，硬拒绝仍走 `invalid_result_json` |
| 生成给模型的规则 | `scripts/_stage5_commands.py` 的 `model_input.rules.interest` | 明示标题文本免计、外围符号计数，且不再与新的计数口径冲突 |
| 契约文档 | `SKILL.md` 第 348 行、`docs/stage5-legacy-contract.md` 第 55/218/301 行 | 三处字数表述与 runner 一致；218 行「恰 3 个非空兴趣段字段」等结构约束未被改写 |
| 校验 agent 口径 | `.apm/agents/professor-contact-email-validator.agent.md` Rule 3 与计数相关表述 | 仍要求标题与 `papers[].title` 逐字一致；如提及字数，与新口径一致 |
| generator 冲突 | `.apm/agents/professor-contact-email-generator.agent.md` 第 44 行起引用 `docs/stage5-legacy-contract.md` 的段落 | 无与新口径矛盾的旧表述；不因口径同步而放宽真实标题要求 |

### 2.6 失败处理

- 断言失败记业务失败，保留首次 `$run_dir` 输出，不放宽断言、不换输入求通过。
- 缺少依赖、解释器或夹具记「无法判断」，停止受影响项，继续可独立项；同一输入最多按一次明确的环境修正重试一次，并保留首次输出。
- 方法或配置确需调整时，先修订本文件对应步骤并记录原因，再由执行者重跑受影响项；无关项不重跑。
- 无外部服务依赖，不设真实模型重采样，不做全仓回归。

### 2.7 有限预检记录

只确认运行环境与资产就位，未取得任何正式结果：

- `py_compile` 通过；`unittest` 收集到 6 个 selector（1 个类，无 immutable 模块的既有用例混入；该模块当前收集 13 个）。
- `python scripts/check_test_shards.py` 报 `OK: 85 test modules across 4 shards, each with a stage`；`--print shard3` 列出 `test_stage5_interest_title_length`。
- 夹具冒烟：既有 `TestStage5.prepare` 能把 80 字符标题写进 `邮件输入.json` 的 `papers[0].title`（实测 `TITLE_LEN 80`），`source_map`/`allowed_sources`/`anchorable_gaps` 与 `validate_email_raw` 的既有要求全部满足（旧口径下三段 142 字符返回空 problem）。
- 语料自检：`interest_corpus` 在 180/181/200/201 四档下「总长 − 标题长度」分别等于目标值（260/261/280/281 − 80），且标题在三段中只出现一次。
- 写入路径冒烟：T4 的第一步用同一标题、净 100（总长 180）的结果 finalize，退出码 0 且三份文件均已生成，说明该夹具能提交一封逐字引用长标题的邮件、保护字符串校验不会因标题变长而误报；T4 的失败点确实落在长度拒绝之后的断言上。
- 为确认失败原因做过一次试跑（不是结果，也不是第三关）：6 个 selector 报 7 个 failure，全部是产品缺失——T1-接受与 T2 净 180 报 `interest total 260 exceeds hard cap 200`（净 180 应无 problem）；T1-规则报旧规则文本不含免计措辞；T2 的 181 报 `interest total 261`（无 181）、200 报硬拒绝（应为 WARNING）、201 报 `interest total 281`（无 201）；T4 的 `message` 是 `interest total 281 exceeds hard cap 200`（无 201）。T3 两个 selector 在基线上通过，属保持行为项，不构成 R1 证据。日志留在 `/tmp/interest-title-length-prep.20261028`。
- 该试跑属于准备期越界：它调用了必测清单里的正式 selector 和 `stage5-finalize` 入口，超出本角色「不执行正式用例」的边界。此处如实披露，不据此声称任何结果或关口状态；第二关前不再调用目标命令，第三关仍须由执行者按本 recipe 首次正式执行。
- 仍缺的输入：产品侧标题免计计数与 `model_input.rules.interest` 新口径尚未实现，因此 T1/T2/T4 在准备基线上按产品缺失失败是预期结果。下一负责人：本地执行工程师。
- 提交后自动 CI（PR #150，shard3）与上述预期一致：`Ran 286 tests`，7 个 failure，全部来自本模块且原因相同——T1-接受与 T2 净 180 报 `interest total 260 exceeds hard cap 200`；T1-规则为旧规则措辞；T2 的 181 报 261、200 报硬拒绝、201 报 281；T4 的 `message` 报 281。T3 两个 selector 为 `ok`。这与准备期试跑的 7 个 failure 逐项相同，属产品缺失，不是测试资产缺陷；登记 shard 后该分片在产品落地前会保持红灯，见 §4 的 R2。

## 3. 证据与状态

不增加真实模型 eval、全教授流程、全仓回归、重复安装、来源认证、自建判定器或完整运行轨迹。生成规则是否使用新口径以 model_input/契约核对，确定性计数以现有框架断言；不是文风质量测试。

- 第一关（必测清单）：通过，见同目录 `review.md`。该记录里的 TP1 SHA-256 `6348e4da…` 对应 recipe 补齐前的版本；本文件 §1 逐字未改（该节内容 SHA-256 `473f1323…`），因此第一关结论继续适用，补齐 recipe 不重开第一关。
- 第二关（具体步骤）：recipe 与 selector 已补齐，本角色准备产物已由独立 `implementation_reviewer` 判「完整」（见 §4，不代表第二关）；第二关仍待独立测试计划审核者，本 PR 不声明已通过。
- 第三关（正式结果）：未执行；产品实现尚未交付，T1/T2/T4 当前按产品缺失失败。
- 下一负责人：测试计划审核者确认第二关；实现/测试工程师补实现；执行工程师执行；独立结果审核者采用实际记录。作者不得自行标注通过。

依据：[Test Engineer Rule](https://app.notion.com/p/3d80101a85f380d8a8f5ce528141e253) 与 [PROJECT_CONSENSUS](https://app.notion.com/p/3d60101a85f3815a8c43f271f2b4d91d)。仅复核受影响项；文档 SHA 改变本身不触发重跑。

## 4. 测试准备符合性审核记录

按 [实现符合性审核入口](https://github.com/ScholarWorkflow/professor-contact) 调用独立 `implementation_reviewer`，对本角色应交付的三项产物（测试模块、shard 登记、本文件 §2 recipe）做只读核对。共 7 轮：前 6 轮为「部分完成」，逐轮指出 T1-规则文本匹配的假失败与假通过（子句共现过严、符号否定子串、括号边界两侧、敬体与复合动词词表、括号内免计标题 vs 符号等），均由本角色修正并交同一入口定向复核。

**第 7 轮结论：完整。** 审核确认：T1–T4 均有对应 selector 与可执行 recipe；断言读取真实可观测量（`validate_email_raw` 返回、wrapper 退出码与 payload、最终文件字节），无自我验证、无跳过、无清单外新增测试项；产品代码与产品文档零改动；§3 未声称任何关口通过或第三关已执行。审核时版本：测试模块 `ebdd8fe3bb4caa3ba8fd08e1db32ea3e700044c0c836e9ab6b58ea954ac690ef`、本文件 `e2a229c935fd7e5b47d381f6f3a8f9ca9fcb357bca9b9d46fda104047731302f`、`shards.json` `4a8039461bacbefec49d24116969f3b4f939781c2dd34ad9f4c4d1e7145429aa`。

**冻结**：T1-规则的文本匹配判定自该版起冻结，不再增加词表或窗口条件。后续若产品 `rules.interest` 的落地文本与判定不兼容，按 Test Engineer Rule 先修本计划再改断言，不在执行阶段临场放宽。§2.4 已写明该判定的已知覆盖边界（`标点忽略` 一类词表外措辞、间隔大于 10 字符、跨子句 `均不计`、完全不提符号的规则），这些属已声明范围，不作为缺陷。

**未解除、按归属移交**：
- R2 待计划负责人：EP1 §1「本 PR 只提交计划和必要审核记录」与本轮已批准准备测试代码、以及 shard3 在产品缺失时 CI 红灯之间的不一致，需计划负责人统一 EP1 范围与落地/CI 预期。本角色不修改 EP1。
- T1 措辞待测试计划工程师：§1 T1「外侧符号计数」目前只有反向证据（「没把符号一起免掉」），完全不提符号的规则会通过。是否收窄 §1 措辞由测试计划工程师裁定；本角色不改必测清单。

本结论仅表示本角色准备产物已落实有效计划，不代表第二关、第三关或合并批准。
