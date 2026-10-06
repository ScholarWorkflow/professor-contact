# Issue 66 第二关口本地权威记录候选

状态：本地候选，**Gate2 待批准**。本记录不构成 Gate2 审核结论或正式运行授权。

## 权威来源与版本

- 有效测试计划：第 4 版完整计划，PR 评论 [5991701404](https://github.com/ScholarWorkflow/professor-contact/pull/73#issuecomment-5991701404)。它取代先前测试计划，并明确不要求修改产品。
- 已批准执行方案：第 13 版，议题评论 [5983011055](https://github.com/ScholarWorkflow/professor-contact/issues/66#issuecomment-5983011055)；批准来源为 PR 评论 [5983107348](https://github.com/ScholarWorkflow/professor-contact/pull/73#issuecomment-5983107348)。这不是 Gate2 批准。
- Gate1：第 6 版 PASS，议题评论 [5988663001](https://github.com/ScholarWorkflow/professor-contact/issues/66#issuecomment-5988663001)。
- 先前候选：第 21 版评论 [5992605405](https://github.com/ScholarWorkflow/professor-contact/pull/73#issuecomment-5992605405)，当前未批准。
- PR #73 目标提交：`dfe430560b6e4d9d85c30b71b8c84bc621da7549`；基准提交：`03dfd501f5212c86356409f7e011f676384f2633`。
- 相关产品代码祖先：`76c0a7b4b329cf31ac8b99b0535c713044ab51a6`；已知缺陷代码基点：`83f1d03251a60f3c00d5c89748f150bfc1daaf25`。本轮为测试、判定和记录工作，不修改产品代码。
- 本地 PR 工作树：`/Users/rekidunois/.codex/worktrees/issue-66-test-engineer/professor-contact`。
- 本地修改涉及判定程序及确定性测试：`.apm/skills/professor-contact/tests/runtime/judge_issue66_stage3_runtime.py`、`test_issue66_runtime_judge.py`、`test_issue66_invocation_credential.py`、`test_issue66_validation_handoff.py`、`test_issue66_stage3_local_state.py`、`test_stage3_idea_generator_agent_contract.py`。这些是本地工作树中的测试侧结果；尚未提交，不作为一个新产品提交号。

## 本地确定性结果

测试均使用 `uv run --python 3.14` 和 `UV_CACHE_DIR=/private/tmp/issue66-uv-cache`。本次记录未保存 `uv --version` 与 Python 完整版本输出；获批执行前须按固定顺序文件记录这两项，不能用本说明推定具体补丁版本。

| 检查 | 命令 | 结果 | 分类 |
| --- | --- | --- | --- |
| Judge 用例 | `UV_CACHE_DIR=/private/tmp/issue66-uv-cache uv run --python 3.14 python -B -m unittest discover -s .apm/skills/professor-contact/tests -p test_issue66_runtime_judge.py -v` | 39/39 通过，退出码 0 | PASS |
| 凭据用例 | `UV_CACHE_DIR=/private/tmp/issue66-uv-cache uv run --python 3.14 python -B -m unittest discover -s .apm/skills/professor-contact/tests -p test_issue66_invocation_credential.py -v` | 15/15 通过，退出码 0 | PASS |
| 本地状态用例 | `UV_CACHE_DIR=/private/tmp/issue66-uv-cache uv run --python 3.14 python -B -m unittest discover -s .apm/skills/professor-contact/tests -p test_issue66_stage3_local_state.py -v` | 12/12 通过，退出码 0 | PASS |
| 交接用例 | `UV_CACHE_DIR=/private/tmp/issue66-uv-cache uv run --python 3.14 python -B -m unittest discover -s .apm/skills/professor-contact/tests -p test_issue66_validation_handoff.py -v` | 20 项：19 通过、1 失败，退出码 1 | 1 项预期产品 FAIL，详见下文 |
| 代理契约用例 | `UV_CACHE_DIR=/private/tmp/issue66-uv-cache uv run --python 3.14 python -B -m unittest discover -s .apm/skills/professor-contact/tests -p test_stage3_idea_generator_agent_contract.py -v` | 9 项：8 通过、1 项测试失败；该项有 3 个失败子断言，退出码 1 | 1 项预期产品 FAIL，详见下文 |
| 拒绝快照定向用例 | 定向子集；凭据拒绝 1/1，交接的 prepare/save/record 拒绝 4/4，均退出码 0 | 全部通过 | PASS；该结果不代表完整文件运行 |

前五条整文件命令由顶层在上述工作树执行；拒绝快照为定向子集。记录中未保留该定向子集的精确测试选择器，因此不把它作为可独立复验的完整文件结果。

## 两项仍存在的产品失败

1. **新调用的第一轮交接目录冲突**：保留上次验证留下的目录后，为同一教授创建新凭据并开始普通生成，新调用的 round 1 prepare 收到 `validation_handoff_collision`。交接文件按教授和轮次定位，不能区分新调用。完整交接文件结果为 19/20；同调用同轮重复 prepare 拒绝、两轮修正和教授隔离已有断言通过。判为产品 FAIL，不修改产品代码。
2. **代理说明仍使用旧交接链**：OpenCode 示例、共同收尾说明和直接记录示例仍与技能中的四步流程不一致。应有流程为 prepare、validator 携带 `output_file` 生成原文、save、record；旧说明仍指向无 `output_file`、复制正文或旧 `--professor-dir --validation-file` 记录方式。代理契约结果为 8/9，新增用例的 3 个子断言均失败。判为产品 FAIL，不修改产品代码。

以上是确定性回归证明的产品失败，不是 `S3-RT-CODEX-1` 的运行结果，也不推导出其余未检查事实的结论。

## 历史结果与当前关口

- 第 17 版正式尝试 `r17-132914` 仍为 FAIL：产品版本 `76c0a7b4b329cf31ac8b99b0535c713044ab51a6`，根线程没有真实委派。保留原结果，不由当前判定程序或候选覆盖。
- Gate1 第 6 版为 PASS；Gate2 第 21 版候选尚未批准。
- 正式运行 `S3-RT-CODEX-1` 未运行。Gate2 仍待批准，固定脚本在没有明确 Gate2 批准证据时必须拒绝继续；不得把第 13 版方案批准或 Gate1 PASS 当作 Gate2 批准。
- 当前状态仅表示所列本地自测结果和两项已复现产品 FAIL。安装、请求、服务存储归属与正式运行证据尚未完成，不能给出 Gate2 PASS。

固定脚本只接受 PR #73 的 Gate2 批准评论作为门禁凭证。评论须逐字包含标记 `ISSUE66_GATE2_APPROVAL_R4: APPROVED`、本文件 SHA-256 和目标 PR head SHA；脚本还会在线核对评论属于 PR #73 且当前 head 未变化。以上是待未来批准时使用的凭证格式，不表示已有批准。

## 获批后唯一正式运行顺序

固定执行文件 `test-plan/issue-66-run.sh` 只校验 Gate2 明确批准并显示下列顺序；它不会启动服务、安装产品、发出请求、运行自测或执行 `S3-RT-CODEX-1`。

1. 固定本地工作树、目标提交、测试侧文件清单、Python 3.14 和 `uv` 实际版本。执行并保留 `uv --version` 与 `uv run --python 3.14 python --version` 输出。保持安装目标为指定产品提交；本地未提交测试修改不能偷偷成为产品安装内容。
2. 只读确认正式安装的锁文件完整指向目标提交，源文件与安装投影一致，无手工修补；记录安装产物版本和路径。核对初始输入摘要、禁止产物缺席、请求配置及来源。
3. 只读识别现存评估服务的实际进程、环境、配置覆盖、数据库和运行记录归属。通过 `direnv exec .` 解析项目配置中的 `EVAL_PORT`，并根据其对应的现存服务入口访问 `/eval`。不得启动、停止或重启服务。数据库路径以服务实际进程和配置为准；若未指定数据库目录，检查进程是否继承 `CODEX_SQLITE_HOME`。服务进程、数据库和日志必须属于本次测试专用存储，禁止从顶层旧数据库推断归属；读出的凭据值不得写入日志。
4. 固定共享环境版本 `c738fa2f8bcbb16cd99d741332d5f59b062b6357` 和适配器约定 `skills-test-fixtures/codex-eval-adapter@16`。逐项核对项目共识指定的实际请求配置，不增加自定默认值；将请求、输入和样例保存到本次独占目录。
5. 请求前对受保护产物保存同一集合的存在性、文件类型和完整字节基准；服务存储只读。每次拒绝后用同一集合比较，不以最终快照替代调用期间的操作证据。所有原始响应、`app_server_events`、命令输出和错误输出写入本次独占证据目录，保留完整尝试。
6. 仅在 Gate2 批准及前置检查均通过后，按冻结的 `S3-RT-CODEX-1` 入口向现存 `/eval` 发出一次请求。读取原始 `app_server_events`，按正式 `sender_thread_id`、真实 `call_id`、子线程、轮次、事件序号、开始和完成返回关联。用真实工具调用和结构化返回判断凭据、交接、原文及权限；消息正文按有序文本块无分隔拼接后以 UTF-8 字节比较。不得以 `commandActions`、兼容投影 `output.events`、最终目录快照或完整子线程业务输入代替这些证据。
7. 对照 r4 固定要求运行判定程序，得到唯一整体结论和逐项证据来源、关联、结论及缺口；将正式归属、安装、存储所有权和证据有效性接入该结论。若出现可归属的产品违反，保留 FAIL；其余外部阻断、无效执行、未测试分支分别按 r4 分类，不相互掩盖。
8. 运行后再次对相同受保护文件集合记录存在性、类型和完整字节，保存本次原始证据、判定输出和历史索引。不得删除失败材料。同条件不自动重试；任何恢复后的复验须先记录恢复事实、受影响用例及批准的复验决定。

## 存储、请求及停止约束

- 产品安装必须来自指定提交的干净消费者；不复制或手工修补安装产物，不使用另起命令、`curl` 或另一个评估会话冒充原生委派。
- 运行、输入、快照、事件、判定和日志放入本次唯一目录；评估服务、数据库和服务日志必须是测试专用。不得连接生产用户状态。
- 服务、数据库和日志均只读检查；不更改服务环境、沙箱权限、产品、正式要求或已批准实施方案。
- 每个正式入口只运行一次。真实机器故障出现时立即停止并保存失败前缀；不得要求未来阶段的证据来否定此前已成立的产品 FAIL。
- 没有 Gate2 明确批准、审批所指提交或候选摘要不匹配、环境/存储归属无法核实时，均不得发出正式请求。
