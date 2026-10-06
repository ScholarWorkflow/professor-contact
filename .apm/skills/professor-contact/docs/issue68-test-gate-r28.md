# 第 72 号拉取请求：测试计划第 25 版实现与合成预检记录

记录编号：`issue68-r28-r25-observation-preflight-2026-10-06`。

**状态：测试实现候选待第二关口审核；第二关口未完成。** 本记录只报告逐次输入观察能力的测试实现和合成预检，不是正式验收结论，也不表示第三关口可以开始。

## 1. 版本依据与替代关系

| 项目 | 固定版本或状态 |
| --- | --- |
| 当前测试计划 | `issue-68-test-plan-r25-2026-10-06`，PR #72 评论 [6010481027](https://github.com/ScholarWorkflow/professor-contact/pull/72#issuecomment-6010481027) |
| 被替代的测试计划 | 第 24 版，PR #72 评论 [6009207405](https://github.com/ScholarWorkflow/professor-contact/pull/72#issuecomment-6009207405)；已由第 25 版完整替代 |
| 批准的产品方向 | `issue-68-plan-r13-2026-10-06`，第 68 号议题评论 `6000673923`；范围更正见评论 `6000931583` |
| 第一关口依据 | `issue-68-gate1-r4-2026-10-05`，第 68 号议题评论 `5981562292` |
| 被测产品目标 | `ScholarWorkflow/professor-contact@b39a4252e3ce473f8cdeedd2e12b0cf86d6f597d` |
| 候选测试改动前基线 | `ScholarWorkflow/professor-contact@1c5023decdcfb22b5d196bf22640b3dab45a7b99` |
| 运行证据契约文件 | `.apm/skills/professor-contact/tests/runtime/issue68-runtime-evidence-contract-r19.json` |
| 本候选测试代码提交 | `fc9a91705a46d0c5eea14310bbe9871b99e00bd0` |

第 25 版是本轮唯一有效的测试计划；第 24 版及更早版本绑定的测试实现结论不能替代本记录。候选测试实现从表中所列基线开始修改。产品目标仍固定为表中所列提交；本轮没有修改产品代码。

## 2. 第 25 版要求与观察边界

第 25 版要求在教授代理正常处理 `owner_input_file` 的原有 JSON 解析路径上，对该次解析结果作只读观察。观察必须能对应到同一运行、正式教授线程、具体调用、所属教授、来源步骤，并能关联首个 `stage5-plan` 结构化输出。连续调用按各自调用编号分别关联。

本实现以一次标准输出中的严格 JSON 信封承载观察记录，并校验 `call_id`、`generation`、正式线程及步骤关联。信封还记录原有 `contact_state.py` 子进程实际收到的 `stage5_invocation.argv` 字符串数组；首个计划调用的 `--result`、`--choices` 判定只读这份同次结构化参数记录，不从 shell 命令文字还原。观察来自原解析路径同次得到的 JSON 解析结果；不再次读取文件，不从命令文字推断已消费的数据，不向提示增加业务内容，也不新增测试专用业务入口。现有教授隔离、路径和标识、根代理结果消费及总览处理约定继续按第 25 版执行。

## 3. 测试实现范围

本候选只修改以下五个测试范围文件：

1. `.apm/skills/professor-contact/tests/runtime/verify_issue68_stage5_routing_r19.py`：解析并判定逐次输入观察及其关联证据。
2. `.apm/skills/professor-contact/tests/runtime/run_issue68_stage5_routing_r19_codex.py`：接入预检及正式入口的启动保护。
3. `.apm/skills/professor-contact/tests/runtime/issue68-runtime-evidence-contract-r19.json`：记录当前证据格式与关联要求。
4. `.apm/skills/professor-contact/tests/runtime/prompts/issue68-stage5-root.txt`：更新测试运行说明，不加入预期业务值或额外业务步骤。
5. `.apm/skills/professor-contact/tests/test_issue68_runtime_r19.py`：为观察解析、证据关联和反例判定提供合成单元用例。

没有修改产品代码。测试实现没有更换正式入口类别、正式验收条件、证明范围或产品行为。

## 4. 合成预检及命令

预检只向判定程序提供合成 JSON 事件，用来检查观察信封、调用与线程关联，以及各类证据的分类。命令从仓库根目录运行：

```bash
uv --cache-dir /private/tmp/issue68-uv-cache run python .apm/skills/professor-contact/tests/test_issue68_runtime_r19.py
```

结果：退出码 `0`；17 项单元测试通过。本次重跑覆盖结构化 `argv` 校验；原先 15 项结果由该结果取代。

运行证据契约的 JSON 语法检查命令：

```bash
jq -e . .apm/skills/professor-contact/tests/runtime/issue68-runtime-evidence-contract-r19.json >/dev/null
```

结果：通过。该命令只确认文件可由 `jq` 解析，不代表契约内容已获审核。

合成预检覆盖以下分类：

| 合成输入 | 预期判定范围 |
| --- | --- |
| 同一调用中合法读取，之后临时文件已清理 | 只接受读取时保存的同次观察证据 |
| 实际读取内容与来源不一致 | 按有效观察确认内容错配 |
| 教授、目标或业务数据错误 | 按有效观察确认归属或业务数据不符 |
| 复合命令的实际 `argv` 含 `--result` 或 `--choices` | 从同次结构化参数证据识别首调违规并判产品失败 |
| 只有命令文字 | 不把命令参数当作实际读取证明 |
| 命令文字写有 `--result` 或 `--choices`，但整个 `stage5_invocation` 字段缺失 | `BLOCKED_OBSERVABILITY`；不按文字内容推断调用参数 |
| 无关读取或调用结束后的读取 | 不把无关或事后读取关联到目标调用 |
| `stage5_invocation` 对象存在，但必需 `argv` 缺失或损坏 | `INVALID_EVIDENCE` |
| 信封格式损坏或关联存在歧义 | 归为无效或不能唯一归属的证据 |

这些结果只说明测试判定程序对合成样例执行了对应分类检查；不证明产品在正式运行中产生了合规观察，也不构成 `PC68-R1` 的通过或失败。

## 5. `PC68-D1` 历史结果的使用边界

第 25 版允许在证明未受本轮改动影响时复用历史证据。以下记录只作为历史 `PASS` 支持证据保留：

| 项目 | 历史记录 |
| --- | --- |
| 运行编号 | `pc68-d1-r29-20261006` |
| 历史产品提交 | `35f2785b4d13783683860db910a36add2347bd29` |
| 历史测试提交 | `e931ab22fbe492bdf0c4ecb74e906d2c23dfce23` |
| 历史组件数 | `43` |
| 历史结果 | `PASS` |

此结果属于上述历史产品与测试版本，不是本记录候选代码上的当前验收，也不把这两个历史提交改记为本轮版本。它仅按第 25 版可复用范围作为历史支持材料保留。

## 6. 当前关口状态与未执行项

- 第二关口仍为 `INCOMPLETE`；本候选需按第 25 版完成独立审核后，才能确定是否冻结。
- `PC68-R1` 本轮未运行。不得把本次合成预检写成正式验收，也不得据此声明任何正式 case 通过。
- `PC68-D1` 仅引用第 5 节列出的历史 `PASS`，不是本轮当前验收结果。
- 既有正式尝试及其原始状态保持不变；本记录不重判或重分类任何历史失败、阻断或未启动结果。
- 第三关口未就绪。

## 7. 项目规则文件可用性

本轮对仓库文件的扫描未找到 `PROJECT_CONSENSUS.md`、`Plan Reviewer Rule.md` 或 `Test Engineer Rule.md`。因此，本记录按当前冻结的第 25 版测试计划和第 13 版批准产品方向约束范围；缺失的项目规则文件没有被视为已阅读或已满足。
