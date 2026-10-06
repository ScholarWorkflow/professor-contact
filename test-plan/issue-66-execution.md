# 第 66 号测试的安装与正式执行接线

本文件是 `issue-66.md` 的固定执行部分，受同一候选及文件摘要约束。依据为第四版证明计划 `issue-66-test-plan-r19-clarification-r4-2026-10-05`。当前第二关口未批准；以下程序为待审实现，不构成执行批准。

## 固定输入和入口

产品完整提交固定为 `dfe430560b6e4d9d85c30b71b8c84bc621da7549`，共享环境完整提交固定为 `c738fa2f8bcbb16cd99d741332d5f59b062b6357`，适配约定为 `skills-test-fixtures/codex-eval-adapter@16`。测试提交从实际仓库 `git rev-parse HEAD` 取得，判定及接线文件按冻结材料的全文件 SHA-256 核对。判定入口为 `judge_issue66_stage3_runtime.py`；接线入口为 `issue66_execution.py`。

在本工作树先执行 `pwd`，将输出原样代入 `REPOSITORY`。进入该目录后执行：

```sh
cd "$REPOSITORY"
bash test-plan/issue-66-run.sh local
```

运行器包含判定 109 项、接线 10 项、结构化记录 5 项、凭据 17 项、本地状态 12 项、交接 22 项、代理说明 9 个方法，共七套件。`tests/runtime/issue66_suite_result.py` 以测试回调保存方法、子测试参数、事件类型及计数，`tests/runtime/issue66_suite_classify.jq` 用结构字段判定，`test_issue66_suite_result.py` 检查合法与异常记录；日志只留作原始材料。当前已知产品失败继续保留。接线确定性检查覆盖请求构造、真实快照、历史不可覆盖、正式关系缺失/冲突、预检不发请求、消费者内初态构造、冻结构造资产拒绝变更及捕获凭据拒绝符号链接；这些检查不代表服务或业务通过。

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

## 现有服务的只读取证

完整预检模式依次取得项目 `direnv exec . printenv EVAL_PORT`，查询该端口唯一监听进程和其实际应用服务子进程，读取实际进程环境及配置，随后执行安装与输入预检。程序不启动、停止或重启服务。

```sh
UV_CACHE_DIR=/private/tmp/issue66-uv-cache \
  bash test-plan/issue-66-formal.sh preflight \
  --fixture-root "$FIXTURE_ROOT" --evidence-dir "$NEW_EVIDENCE_DIRECTORY" \
  --service-contract "$SHARED_SERVICE_CONTRACT"
```

`SHARED_SERVICE_CONTRACT` 必须来自项目指定的共享环境配置并由本候选审核固定，不得临时填一个通过标记。固定字段为 `service_isolation_root`（该测试专用服务存储的绝对根目录）和 `authority`（项目指定来源）。程序保存该文件实际摘要，冻结材料也必须核对同一摘要。**当前尚未取得这个来源文件及实际存储根**，这是现实环境缺口，不能用自行指定临时路径掩盖。

采集程序先以 `lsof` 定位监听进程，再以 `ps` 核对其应用服务后代。实际进程环境仅保存 `CODEX_HOME`、`CODEX_SQLITE_HOME` 和负责隔离的目录变量；其他环境内容不落盘。实际 `CODEX_HOME/config.toml` 用 `yq` 解析，不从用户目录猜默认配置。数据库目录优先按实际配置 `sqlite_home`，未指定时检查进程继承的 `CODEX_SQLITE_HOME`，再按实际测试专用 `CODEX_HOME` 解析。数据库及日志取实际打开文件，不能拿顶层旧数据库代替。

服务根、配置、实际数据库和日志均须位于共享来源指定的测试专用根。正式运行后以 SQLite `mode=ro` 和 `query_only=ON` 查询实际 `threads.id/rollout_path`，只读取本次根和正式子线程记录；线程与运行日志必须归属本次实际响应及测试专用目录。实际架构或打开文件形状不支持已写采集时记录具体缺口并停止，不改配置、不启停服务、不扩大权限。

当前端口读取退出 1、没有端口；因此服务配置、存储和线程归属尚未核实。安装预检可独立进行。`storage-preflight.json` 中正式线程尚未产生的 `run_records_match_case` 不通过仅表示未来事实未到达，不据此宣称实际业务失败。

固定程序的实际完整预检证据为 `issue66-service-preflight-20261006`：程序退出 2、`CASE_NOT_STARTED`，命令 `12-eval-port` 退出 1、未返回端口，在安装和请求前停止。专用存储来源仍未取得，不以自行指定目录代替。

## 冻结后的唯一正式执行

正式执行只能在第二关口完整批准当前测试提交后进行。冻结材料 JSON 字段为 `plan`、`product_commit`、`test_commit`、`fixture_commit`、`gate2_comment_id`、`gate2_reviewer`、`service_contract_sha256` 和 `files`（仓库相对路径到 SHA-256 的映射）。至少覆盖本文件、正式脚本、执行接线和唯一判定程序；审核应固定全体测试文件及其直接依赖。正式模式查询真实远端批准评论，核对审核者、当前完整提交及同一计划，核对全部冻结文件，工作树必须无修改。没有冻结批准时停止，预检则始终无需批准。

```sh
UV_CACHE_DIR=/private/tmp/issue66-uv-cache \
  bash test-plan/issue-66-formal.sh formal \
  --fixture-root "$FIXTURE_ROOT" --evidence-dir "$NEW_EVIDENCE_DIRECTORY" \
  --service-contract "$SHARED_SERVICE_CONTRACT" \
  --frozen-manifest "$APPROVED_FROZEN_MANIFEST"
```

程序固定顺序：版本及批准 → 项目端口 → 服务和存储隔离 → 全新正式安装 → 初态摘要及禁止产物 → 固定请求 → 前快照 → 一次既有服务 `POST /eval` → 原始响应 → 精确版本适配器 → 后快照 → 正式关系派生 → 实际凭据字节和资料字节 → 只读运行存储归属 → 唯一判定。每一步实际命令、目录、退出码、输出摘要及原始输出保存在 `commands`，一次请求编号保存在 `attempt.json`。

原始响应及适配器输出分别保留为 `response-raw.json` 和 `adapter-raw.json`；加入同一 `evidence_set_id` 的派生副本不覆盖它们。捕获凭据从实际成功完成命令的结构化返回定位，读其真实 UTF-8 字节及固定初态资料字节，不从最终状态倒推捕获内容，不增加未设计的完整文件操作监视。正式关系按 `sender_thread_id` 归属，仅派生实际直属、嵌套及冲突关系；失败前缀尚未到达的生成/校验数量由唯一判定按实际阶段处理。

统一判定一次性接入 `install.json`、`fixture.json`、`routing.json`、`pre.json`、`post.json`、`storage.json`、完整响应、适配器和实际候选状态及程序根。它负责整体分类、逐事实来源和缺口。根消息/子线程结果、原文生产、写权限、完成顺序及停止条件按完整原始事件处理；人工备注没有程序外通过权。失败前缀不调用旧验证器的未来完整终态检查。

正式请求最多一次，无自动重试。不论成功、失败、无效还是外部阻断，全部原始材料保留；恢复事实及复验决定未成立时不另发请求。请求前前提失败为 `CASE_NOT_STARTED`；请求已发但原始响应不可解析或不能归属时保留 `INVALID_TEST_EXECUTION`，不把未知启动边界假称已开始或未开始。已有独立产品违反由统一判定保留，不被后续存储缺口覆盖。

## 已核对能力和剩余范围

最终确定性预检见 `issue66-gate2-candidate.iTkWhAuh`，七套件依次 109、10、5、17、12 项通过，22 项交接含 1 个产品失败、9 个代理说明方法含 3 个失败子测试；整体 `FAIL`、退出 1，账本有效。122 次判定调用、245 条断言与 60 行 24 列样例全部留存；判定诊断 `[]`、账本校验 `true`。结构字段由 `jq 1.8.2` 解析，安装配置由 `yq 4.53.3` 解析。旧无效尝试和复验决定见主记录，未覆盖或删除。

本次最后填报只更新两份说明，复用该轮七套件、程序哈希及账本实际记录。原前后摘要绑定填报前文件；最终报告候选另由顶层全文件摘要清单冻结，不把旧摘要写成当前报告摘要。

可信历史探测原始响应摘要为 `57ff0300b3e269edbabd11fae6e24e6a62afebabb028dcbd7dca995b6b83ffc8`，适配器输出摘要为 `46406d63ea382759c958326f12e7ee68d8cd8f6d8168ab8cca89f81c99975316`。对应 `codex-cli 0.159.0-alpha.12.1`、59 条原始事件；序号 21802/21803 共享线程、轮次和消息编号，完整正文一致，21815 为根接收。离线重解析确认正式直属关系，原探测没有指定业务代理目标，没有业务文件生产。因此只复用关系及业务消息能力，不把旧适配器就绪当当前命名代理、安装、存储、生产或权限通过。

安装命令的真实预检退出 0，消费者证据基名为 `issue66-install-preflight.p00XRJAK`。首次安装检查 `issue66-install-check-20261006` 退出 2，判为 `CASE_NOT_STARTED`：已安装构造辅助将消费者视作生产仓库，拒绝其内部 `program`。保留旧失败，改用核对固定源字节的本仓库纯初态资产；没有重装或修补消费者。新独占尝试 `issue66-install-check-fixed-20261006` 退出 0，安装投影、初态、请求和前快照已核实，没有发送正式请求。

新增三项回归在修复前运行 10 项，退出 1，三项报错；修复后同组运行 10 项，退出 0。原始输出分别为 `issue66-wiring-fix-before.stdout/.stderr` 和 `issue66-wiring-fix-after.stdout/.stderr`，均保留。随后将固定构造资产检查接入初态证据，并把复用消费者的 `newly_created` 更正为 `false`；同组最终检查 `issue66-wiring-fix-final.stdout/.stderr` 仍为 10 项、退出 0。真实安装复验记录原样保留，其中原 `newly_created=true` 为测试元数据错误，实际来源为已有消费者，不能据此声称新安装。实际服务配置、存储架构和正式业务取证尚未通过，待审程序写完不等于这些现实前提通过。完整用例对应、逐项复验依赖、历史失败和历史有效来源继续在同一候选 `issue-66.md` 登记，不以本文件代替未完成项。
