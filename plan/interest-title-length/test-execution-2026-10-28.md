# 兴趣段字数不计论文标题 — 测试执行记录（2026-10-28）

- 执行计划：EP1（`Plan conclusion: APPROVED`，P1–P4 PASS），需求 R1。
- 测试计划：TP2；第 1 节必测清单未改，第一关沿用 `review.md` 的通过记录；第二关仍待独立审核，本记录不自授通过。
- 产品基线：`b67dd3ca4d29dfc78f57988564b219c71b582674`（main）。
- 测试资产基线：`fe9ee442b0656a4b5fa549821fbb2c81d0cbc24f`（本轮执行前的 PR head，测试模块与 recipe 已按 TP2 对齐）。
- 受测产品版本：`ef0727b`（`fix(stage5): exclude verbatim cited paper titles from interest length`，本轮唯一的实现提交）。T1–T4 与 shard3 执行时，工作树的产品文件相对 `fe9ee44` 已有未提交改动；该改动与 `ef0727b` 逐字节相同（提交后 `git diff ef0727b -- .apm` 为空），因此本记录把 `ef0727b` 记为受测版本。
- 环境：macOS arm64；解释器 `/run/current-system/sw/bin/python3`（Python 3.14.7）；从 PR 工作树根目录执行，产物写在仓库外运行目录。
- 运行目录：`/tmp/interest-title-length-run.20261028`，其中 `target-version.txt`、`python-version.txt` 记录版本，`t1.log`/`t1.exit`、`t1-rule.txt`/`t1-rule.err`/`t1-rule.exit`、`t2.log`/`t2.exit`、`t3.log`/`t3.exit`、`t4.log`/`t4.exit`、`shard3.log`/`shard3.exit` 保存本次原始输出。`TMPDIR` 指向该目录，`BaseEnv` 的临时邮件文件全部落在其中并在 teardown 删除。仓库外原始产物不入库，本记录只保存脱敏结果。
- 运行目录偏离说明：TP2 §2.3 的模板是 `run_dir=$(mktemp -d /tmp/interest-title-length.XXXXXX)`，本轮改用固定目录 `/tmp/interest-title-length-run.20261028`，便于把六项输出放在同一处并逐项写退出码。该目录创建于 13:25:00，早于本轮首次执行，且与准备期目录 `/tmp/interest-title-length-prep.20261028`（创建于 00:05:08）分离，只含本轮输出；隔离与输出完整性不受影响，命令、输入和预期均未变，因此不重跑。

## 1. 实现内容（供核对，不代替测试）

按 EP1 §3 的四步：

1. `scripts/_stage5_email.py` 的共享 `validate_email_raw` 增加 `cited_title_chars`：只把当前邮件包 `papers[].title` 中的非空字符串标题，在三段里实际完整逐字出现的字符算作免计；书名号、引号、标点和其他正文仍计入。同一字符位置只扣一次（标题互相包含时不重复扣除），标题跨两段拼出不算命中。
2. 阈值仍为 `INTEREST_SOFT_CAP=180`／`INTEREST_HARD_CAP=200`，仍走同一条 `WARNING` 前缀与硬拒绝通道；plan 与 finalize 继续调用同一 validator，写前检查顺序未变，正文未被改写。
3. 同步 `_stage5_commands.py` 的 `model_input.rules.interest`、`SKILL.md` 第 348 行、`docs/stage5-legacy-contract.md` 第 55／218／301 行的字数口径。email-validator 的 Rule 3（标题与 `papers[].title` 逐字一致）本来就没有字数表述，未改；generator 只引用该契约，也未出现冲突措辞，未改。

## 2. 逐项结果

| 项 | 结果 | 证据 |
| --- | --- | --- |
| T1-接受 | 通过 | `t1.exit=0`；`t1.log`：`Ran 1 test`、`OK` |
| T1-生成规则 | 通过（人工观察一次） | `t1-rule.exit=0`；`t1-rule.txt` 全文见 §3 |
| T2 净正文 180／181／200／201 | 通过 | `t2.exit=0`；`t2.log`：`Ran 1 test`、`OK`（4 个 `subTest` 全部通过） |
| T3 包外标题不免计、无标题包保持原口径 | 通过 | `t3.exit=0`；`t3.log`：`Ran 2 tests`、`OK` |
| T4 净 201 拒绝且不覆盖原邮件 | 通过 | `t4.exit=0`；`t4.log`：`Ran 1 test`、`OK` |
| shard3 全分片（非必测，实现自检） | 通过 | `shard3.exit=0`；`shard3.log`：`Ran 285 tests in 136.940s`、`OK` |

实际命令（在同一 shell 中按 TP2 §2.4 逐项执行，各项分别保存退出码）：

```bash
checkout=$(git rev-parse --show-toplevel)
run_dir=/tmp/interest-title-length-run.20261028
export TMPDIR="$run_dir"
cd "$checkout/.apm/skills/professor-contact/tests"
/run/current-system/sw/bin/python3 -m unittest -v \
  test_stage5_interest_title_length.TestStage5InterestTitleLength.test_t1_long_cited_title_is_accepted_and_rendered_verbatim \
  > "$run_dir/t1.log" 2>&1; printf '%s\n' "$?" > "$run_dir/t1.exit"
# T1-生成规则、T2、T3、T4 同 TP2 §2.4 的命令块，输出分别写 t1-rule.*、t2.*、t3.*、t4.*
```

`git rev-parse HEAD` 在正式执行前记录为 `fe9ee442b0656a4b5fa549821fbb2c81d0cbc24f`（`target-version.txt`）；执行时产品文件已按 §1 改好但尚未提交，随后提交为 `ef0727b`。命令与输入在两者之间未变，且 `git diff ef0727b -- .apm` 为空，所以 §2 的结果对应 `ef0727b`。

### 2.1 T1-接受

`interest_corpus(TITLE, 180)` 生成三段：含 80 字符标题的总长 260，净正文 180。断言读到：

- `validate_email_raw` 返回空列表（净 180 未越软上限）；
- `stage5-finalize` 返回 `status=ok`；
- `套磁邮件.txt` 含按换行拼接的三段原文、完整标题与六个固定标记（`FIXED-BEGIN`、`FIXED-SELFINTRO`、`FIXED-INTEREST`、`FIXED-FUTURE`、`FIXED-LEARNING`、`FIXED-END`）；`套磁邮件.md` 同样含完整标题。

基线上同一输入报 `interest total 260 exceeds hard cap 200`（准备期试跑与上一轮 CI 均为该失败），本轮不再出现。

### 2.2 T1-生成规则（人工观察，无自动判定）

从正式 `stage5-plan` 输出读到完整的 `model_input.rules.interest`（原文见 §3），对照 TP2 §2.4 的三个观察点：

1. 兴趣段仍为三部分，保留原 180 字符软限制 —— 满足：开头「3 句、只写软层」，中段「净正文软上限 ≤180 日文字（runner：>180 警告、>200 拒绝）」，后接 ①②③ 三个部分的定义。
2. 当前邮件包中实际完整逐字引用的论文标题文本免计 —— 满足：「当前邮件包 papers[].title 中实际完整逐字引用的论文标题文本不计入字数」。
3. 标题外的书名号、引号、标点和其他正文字符继续计数，且没有相矛盾的文字 —— 满足：「标题以外的书名号、引号、标点和其他正文照常计入」，同段内没有与之相反的表述。

结论：T1-生成规则通过。`t1-rule.exit=0` 只证明取到了文本，通过结论来自上述阅读。

### 2.3 T2 四个边界

`INTEREST_SOFT_CAP=180`、`INTEREST_HARD_CAP=200` 断言仍成立。四个 `subTest` 全通过，说明：

- 净 180：无长度问题；
- 净 181、净 200：恰好一条以 `WARNING` 开头的长度问题，提示数字包含相应净长度；
- 净 201：恰好一条不以 `WARNING` 开头的长度问题，提示数字包含 201。

### 2.4 T3 两项保持行为

- 包外标题：把邮件包没有的标题形文本放进第②部分，净正文 201、总长 289，得到一条硬拒绝且显示总长 289，说明任意引号内容不会得到免计。
- 无标题包：移除 `papers` 后用同一语料（总长 260），共享 validator 硬拒绝并报告 260，说明没有可信标题时保持原计数。该输入只用于核对计数，不代表满足完整邮件的标题引用要求。

### 2.5 T4 拒绝不覆盖

先以净 100（总长 180）成功 finalize，保存 `套磁邮件.md`、`套磁邮件.txt`、`套磁邮件状态.json` 三份文件字节；再以净 201 finalize，退出码非零、`status=error`、`reason_code=invalid_result_json`、提示含 201，三份文件字节均未变化。

### 2.6 T4 人工静态核对（TP2 §2.5）

| 核对点 | 结果 | 依据 |
| --- | --- | --- |
| 三部分结构、② 1–3 篇与标题真实、③ 与未来志向、source_map | 未放宽 | `_stage5_email.py` 的 diff 只替换长度计算并新增 `cited_title_chars`；`source_map ④ is retired`、③ 只锚 `anchorable_gaps`、`done_by_self` 禁锚等分支逐行未变 |
| 计数只免标题、外围符号仍计 | 符合 | 豁免来源只取 `email["papers"][].title` 的字符串；同一字符位置用集合去重；每段独立扫描，标题不跨段拼合；正文未被改写 |
| 阈值与警告/错误通道 | 符合 | `contact_state.py` 的 `INTEREST_SOFT_CAP=180`、`INTEREST_HARD_CAP=200` 未变；warning 仍带 `WARNING` 前缀并被 plan/finalize 过滤，硬拒绝仍为 `invalid_result_json` |
| 契约文档 | 一致 | `SKILL.md` 第 348 行、`stage5-legacy-contract.md` 第 55／218／301 行均改为净正文口径；218 行「恰 3 个非空兴趣段字段」等结构约束保留 |
| 校验 agent 口径 | 一致 | email-validator Rule 3 仍要求标题与 `papers[].title` 逐字一致；该文件本来没有字数表述，本轮未改 |
| generator 冲突 | 无 | generator 引用 `docs/stage5-legacy-contract.md`，该文件已同步；generator 自身没有与净正文口径矛盾的旧表述，未改 |

## 3. T1-生成规则原文

`$run_dir/t1-rule.txt` 的完整内容：

```
3 句、只写软层；长度按净正文计：当前邮件包 papers[].title 中实际完整逐字引用的论文标题文本不计入字数，标题以外的书名号、引号、标点和其他正文照常计入；净正文软上限 ≤180 日文字（runner：>180 警告、>200 拒绝）；①真实关注（普通发信人的接触、有限认识与自然好奇，禁恭维）②点名+桥接（真实标题、共同主题逐篇成立）③宽泛例子（仅可用 gaps 里 status∈{open,partial,unknown} 的精确 gap；done_by_self 禁锚；partial 只谈 remaining_gap；引用教授原话式，不找碴）
```

`t1-rule.err` 为空。

## 4. 补充事实：提交后的自动 CI

`9134bb7` 推送后的 CI（run 40638384011）四个分片全部通过；其中 shard3 为 `Ran 285 tests in 145.500s`、`OK`，与本地 §2 的 shard3 结果一致（本地 136.940s，差异属运行时间）。这与准备期和 TP2 对齐后记录的 6 个产品缺失失败形成对照，说明该分片在产品落地后转绿。自动 CI 仍是补充事实，不替代第三关结论。

## 5. 范围授权与计划文本的不一致（如实披露）

EP1 §1 写的是「本 PR 只提交计划和必要审核记录；不修改产品或测试实现，不执行正式测试」，而本 PR 现在包含产品实现（`ef0727b`）、测试模块与 shard 登记（`fe9ee44` 之前的准备提交）以及本执行记录。TP2 §4 已把这件事作为 R2 挂给计划负责人，但本记录此前没有披露。现补充：

- 用户在本轮直接指令「只干活然后推送到 pr」，并把 PR #150 交给本地执行工程师；这是在 EP1 已 APPROVED、TP2 已有可执行 recipe 之后，由验收决定人对「推进到实现与执行」的明确授权。
- 该授权只覆盖推进阶段，没有改变 R1 的需求、EP1 §1 的计数边界、TP2 §1 的必测清单或任何通过条件；因此本轮不重新解释计划，也不把 docs-only 表述当成本轮新增约束。
- EP1 §1 的文本仍未修改，统一由计划负责人处理；本角色不编辑 EP1。若计划负责人认定该句仍需保留，则应把「实现与执行」另立计划，届时本 PR 的产物归属需重新确认。

## 6. 未完成项与下一负责人

- 第二关（具体步骤）仍待独立审核；本轮没有修改测试步骤、输入或预期。
- 第三关的正式结论由结果审核者按本记录与 `shard3.log` 核对；本记录不声称合并条件满足。
- 自动 CI 的 shard3 结果作为补充事实记录，不替代本功能的必测结论。
- 未新增真实模型 eval、全教授流程、全仓回归或重复安装；T3 两项在基线上也通过，属保持行为项，不构成 R1 证据。
- 测试模块顶部注释原写「prepared, not executed / 预期产品缺失失败」，实现落地后已更新为当前状态；只改注释，5 个 selector 的输入、断言与预期未变。改后重跑整个模块得 `Ran 5 tests`、`OK`，§2 的逐项结果继续有效。
- 下一负责人：计划负责人统一 EP1 §1 的范围表述；测试计划工程师更新 TP2 §3／§5 的状态文字并复核第二关；合并审核按 `Merge Reviewer Rule.md` 另走。
