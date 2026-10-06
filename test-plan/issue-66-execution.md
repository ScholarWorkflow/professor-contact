# 第 66 号测试的安装与正式执行接线

本文件是 `issue-66.md` 的固定执行部分，受同一候选及文件摘要约束。当前候选为 R6：`issue-66-test-plan-r19-clarification-r6-2026-10-07`，在 R5 基础上按本地测试工程师的工作要求修订测试工作树位置，并移除评测服务内部状态检查。R5 的服务、存储检查记载只保留为历史，不再作为当前门槛。当前第二关口未批准；以下程序为待审实现，不构成执行批准。

## 固定输入和入口

产品完整提交固定为 `dfe430560b6e4d9d85c30b71b8c84bc621da7549`，共享环境完整提交固定为 `c738fa2f8bcbb16cd99d741332d5f59b062b6357`，适配约定为 `skills-test-fixtures/codex-eval-adapter@16`。测试提交从实际仓库 `git rev-parse HEAD` 取得，判定及接线文件按冻结材料的全文件 SHA-256 核对。判定入口为 `judge_issue66_stage3_runtime.py`；接线入口为 `issue66_execution.py`。

测试工作树必须放在项目 `.envrc` 所在目录之下，例如 `<skill-repos-dev>/worktrees/<branch>`。执行器以 `--repository` 指定的工作树作为 `direnv exec .` 的工作目录，再读取 `EVAL_PORT`。Codex 默认的 `~/.codex/worktrees/...` 不在项目 `.envrc` 的目录树内，按这个目录运行会因找不到环境文件而失败。先在正确工作树执行 `pwd`，将输出原样代入 `REPOSITORY`，再运行：

```sh
cd "$REPOSITORY"
bash test-plan/issue-66-run.sh local
```

R6 七套件实跑数量依次为判定器 113、接线 11、结构化记录 9、凭据 17、本地状态 12、交接 22、代理说明 9 个方法。前五套件通过，后两套保留既有产品失败。`tests/runtime/issue66_suite_result.py` 以测试回调保存方法、子测试参数、事件类型及计数，`tests/runtime/issue66_suite_classify.jq` 判定套件，`tests/runtime/issue66_candidate_classify.jq` 先检查证据有效性再汇总整体及独立产品失败；`test_issue66_suite_result.py` 验证四种组合，原始输入、独立预期及实际结果保存在 `candidate-combinations`。整体输出为 `candidate-result.json`，包含证据有效性、整体分类、局部失败与来源、缺口；`runner_execution=COMPLETE` 仅表示全部步骤执行完毕，不表示账本有效或候选、正式验收通过。各本地命令的原始输出仍原样保存。接线检查覆盖请求构造、快照、历史保留、正式归属、预检不发请求、初态构造、冻结资产及符号链接拒绝。

安装、初态和请求可独立预检，无须端口或第二关口批准。夹具路径由项目指定的精确版本检出目录取得，必须提供绝对路径；证据目录为从未存在过的独占目录，程序拒绝覆盖。

```sh
UV_CACHE_DIR=/private/tmp/issue66-uv-cache \
  bash test-plan/issue-66-formal.sh installation-check \
  --fixture-root "$FIXTURE_ROOT" --evidence-dir "$NEW_EVIDENCE_DIRECTORY"
```

程序在证据目录下创建干净消费者，执行唯一安装命令：

```sh
apm install --target codex \
  'ScholarWorkflow/professor-contact#dfe430560b6e4d9d85c30b71b8c84bc621da7549'
```

若顶层已按该命令在独占临时消费者执行安装，可在 `installation-check` 追加 `--consumer "$INSTALLED_CONSUMER"` 核验该已有产物。该分支不再次安装，也不修补消费者；正式模式不接受复用消费者。工具版本及实际安装输出另行保留，不以目录存在替代正式安装来源。

程序用 `yq` 解析锁文件，核对唯一 `professor-contact.resolved_commit` 为完整目标提交；技能正文和状态脚本与目标提交原始字节比较，三个已安装代理的 TOML 用 `yq` 解码正文再与目标代理正文比较。任何不符停止，保留完整输出。纯初态使用本仓库 `tests/runtime/prepare_issue55_stage3_fixture.py`，调用前将该文件及其直接辅助 `fixture_support.py` 与固定产品提交的原始字节比较，保存 `initial-builder.json`。该纯输入构造资产写入消费者内的 `program`，不复制或修补安装产物，不扩大沙箱。核对实际 `initial-input.json.input_hashes` 的全字节摘要、人工补丁标记及候选、总览、选择、邮件输入缺席。该程序不代写候选或校验原文。

请求构造使用共识指定的默认模型 `gpt-6-luna`、思考级别 `low` 和 `workspace-write`，不指定替代提供方。动态信任键按服务文档支持的完整 `projects` 内联表编码，包含空格或句点的路径不拆开。最多四个业务子线程加根线程，因此资源上限固定为五；业务并发和顺序仍由产品及判定负责。提示词仅要求现有输入的第三阶段，不诱导失败或增加模型次数。请求、提示词和摘要分别保留。

## 评测服务配置约定

完整预检只从项目 `.envrc` 读取 `EVAL_PORT`，然后检查安装、输入、请求和前快照；不会查询监听进程、服务进程环境、`config.toml`、数据库或日志文件。项目评测配置负责给服务实例设置独立的 `CODEX_HOME`。本地测试依赖这项现有配置约定，不再重复验证服务内部文件；评测配置本身属于评测环境配置，不属于本地测试结果。

```sh
UV_CACHE_DIR=/private/tmp/issue66-uv-cache \
  bash test-plan/issue-66-formal.sh preflight \
  --fixture-root "$FIXTURE_ROOT" --evidence-dir "$NEW_EVIDENCE_DIRECTORY"
```

2026-10-07 的 R5 只读诊断曾在错误工作树路径调用端口读取，随后读取进程、配置、数据库和日志并记录了未通过项。这些结果只说明当时的采集方法不适用；新路径已确认能从上级 `.envrc` 取得 `EVAL_PORT`。R6 删除上述服务内部检查，也不再要求 `SHARED_SERVICE_CONTRACT`。

## 冻结后的唯一正式执行

正式执行只能在第二关口完整批准当前测试提交后进行。冻结材料 JSON 字段为 `plan`、`product_commit`、`test_commit`、`fixture_commit`、`gate2_comment_id`、`gate2_reviewer` 和 `files`（仓库相对路径到 SHA-256 的映射）。至少覆盖本文件、正式脚本、执行接线和唯一判定程序；审核应固定全体测试文件及其直接依赖。正式模式查询真实远端批准评论，核对审核者、当前完整提交及同一计划，核对全部冻结文件，工作树必须无修改。没有冻结批准时停止，预检则始终无需批准。

```sh
UV_CACHE_DIR=/private/tmp/issue66-uv-cache \
  bash test-plan/issue-66-formal.sh formal \
  --fixture-root "$FIXTURE_ROOT" --evidence-dir "$NEW_EVIDENCE_DIRECTORY" \
  --frozen-manifest "$APPROVED_FROZEN_MANIFEST"
```

程序固定顺序：版本及批准 → 项目端口 → 全新正式安装 → 初态摘要及禁止产物 → 固定请求 → 前快照 → 一次既有服务 `POST /eval` → 原始响应 → 精确版本适配器 → 后快照 → 正式关系派生 → 实际凭据字节和资料字节 → 唯一判定。每一步实际命令、目录、退出码、输出摘要及原始输出保存在 `commands`，一次请求编号保存在 `attempt.json`。

原始响应及适配器输出分别保留为 `response-raw.json` 和 `adapter-raw.json`；加入同一 `evidence_set_id` 的派生副本不覆盖它们。捕获凭据从实际成功完成命令的结构化返回定位，读其真实 UTF-8 字节及固定初态资料字节，不从最终状态倒推捕获内容，不增加未设计的完整文件操作监视。正式关系按 `sender_thread_id` 归属，仅派生实际直属、嵌套及冲突关系；失败前缀尚未到达的生成/校验数量由唯一判定按实际阶段处理。

统一判定一次性接入 `install.json`、`fixture.json`、`routing.json`、`pre.json`、`post.json`、完整响应、适配器和实际候选状态及程序根。它负责整体分类、逐事实来源和缺口。根消息/子线程结果、原文生产、写权限、完成顺序及停止条件按完整原始事件处理；人工备注没有程序外通过权。失败前缀不调用旧验证器的未来完整终态检查。

正式请求最多一次，无自动重试。不论成功、失败、无效还是外部阻断，全部原始材料保留；恢复事实及复验决定未成立时不另发请求。请求前前提失败为 `CASE_NOT_STARTED`；请求已发但原始响应不可解析或不能归属时保留 `INVALID_TEST_EXECUTION`，不把未知启动边界假称已开始或未开始。已有独立产品违反由统一判定保留。

## 已核对能力和剩余范围

第五版最终确定性预检为 `issue66-gate2-candidate.4LPblyY0`：七套件依次 113、10、9、17、12 项通过，22 项交接含 1 个既有产品失败、9 个代理说明方法含 3 个既有失败子测试；整体 `FAIL`、退出 1、证据有效、缺口数组为空。128 次判定调用、261 条断言（249 条判定相关）、66 行 24 列样例留存；账本校验 `true`、诊断 `[]`。首轮 `Xalmaqxa` 因三处旧计数为 `INVALID_TEST_EXECUTION`，修正后复判及最终独占运行均保留，来源和摘要见主记录。第四版 `iTkWhAuh` 的 109/10/5/17/12/22/9 计数、122 次调用及 60 行样例只作历史。最后填报只更新两份说明，复用最终轮程序及样例检查，以独立全文件清单冻结填报后的候选，不冒用旧摘要。

第五版改变停止判定、样例及候选汇总，重新核验相应依赖。唯一同轮结构化错误报告与根接收事件不算继续业务，停止事实通过不消除业务未完成；失败后依赖业务续行、第二条报告或成功报告仍被拒绝。实际运行系统失败沿用旧失败前缀证据，不要求故障后最终消息。最终报告候选由顶层全文件摘要清单冻结，不把历史摘要写成当前摘要。

可信历史探测原始响应摘要为 `57ff0300b3e269edbabd11fae6e24e6a62afebabb028dcbd7dca995b6b83ffc8`，适配器输出摘要为 `46406d63ea382759c958326f12e7ee68d8cd8f6d8168ab8cca89f81c99975316`。对应 `codex-cli 0.159.0-alpha.12.1`、59 条原始事件；序号 21802/21803 共享线程、轮次和消息编号，完整正文一致，21815 为根接收。离线重解析确认正式直属关系，原探测没有指定业务代理目标，没有业务文件生产。因此只复用关系及业务消息能力，不把旧适配器就绪当当前命名代理、安装、存储、生产或权限通过。

安装命令的真实预检退出 0，消费者证据基名为 `issue66-install-preflight.p00XRJAK`。首次安装检查 `issue66-install-check-20261006` 退出 2，判为 `CASE_NOT_STARTED`：已安装构造辅助将消费者视作生产仓库，拒绝其内部 `program`。保留旧失败，改用核对固定源字节的本仓库纯初态资产；没有重装或修补消费者。新独占尝试 `issue66-install-check-fixed-20261006` 退出 0，安装投影、初态、请求和前快照已核实，没有发送正式请求。

新增三项回归在修复前运行 10 项，退出 1，三项报错；修复后同组运行 10 项，退出 0。原始输出分别为 `issue66-wiring-fix-before.stdout/.stderr` 和 `issue66-wiring-fix-after.stdout/.stderr`，均保留。随后将固定构造资产检查接入初态证据，并把复用消费者的 `newly_created` 更正为 `false`；同组最终检查 `issue66-wiring-fix-final.stdout/.stderr` 仍为 10 项、退出 0。真实安装复验记录原样保留，其中原 `newly_created=true` 为测试元数据错误，实际来源为已有消费者，不能据此声称新安装。R5 对实际服务配置和存储架构的检查只作历史保留；R6 已移除这些本地检查，不把它们列为待办。正式业务事实须在 Gate 2 获批后的真实运行中判定。完整用例对应、逐项复验依赖、历史失败和历史有效来源继续在同一候选 `issue-66.md` 登记。
